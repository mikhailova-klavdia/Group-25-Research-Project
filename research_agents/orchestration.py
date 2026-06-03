"""Code-driven worker plus critic orchestration for ReAct runs.

The worker remains the normal ReAct agent. The critic is invoked by host
code after a worker attempt, so the worker cannot skip review. Dependency
retries are handled deterministically before the LLM critic runs: if the
captured tool output shows a missing Python module, the orchestrator tries
to install the corresponding package into the shared per-paper venv and
then retries the worker once.
"""

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agents import Agent, RunHooks, Runner

from research_agents.agents.critic_agent import CriticReview, create_critic_agent
from research_agents.agents.react_agent import ReActAnswer, create_react_agent
from research_agents.config import DEFAULT_MODEL
from research_agents.hitl import apply_integrity_guard
from research_agents.project import ResearchContext, _find_python_in_venv
from research_agents.tools.exec_tools import MAX_TIMEOUT


# Type alias for a worker-agent factory: takes a model name, returns an
# Agent producing a ReActAnswer.  Teams pass either ``create_react_agent``
# (baseline) or ``create_react_agent_improved`` (the worker-critic-plus
# variant with the extra ESM-2 and synthesis bullets) without needing to
# change orchestration internals.
WorkerFactory = Callable[[str], Agent[ResearchContext]]


_MISSING_MODULE_RE = re.compile(
    r"(?:ModuleNotFoundError|ImportError):\s+No module named\s+['\"]?([^'\"\s]+)"
)

# execute_command always prefixes its result with "Exit code: N"; read tools
# (read_paper, read_repo_file, search_repo, …) never do.  Checking for this
# prefix reliably separates execution outputs from read outputs.
_EXEC_OUTPUT_PREFIX = "exit code:"


def _execution_was_attempted(outputs: list[str]) -> bool:
    """Return True if any captured output came from an execute_command call.

    Used to guard against applying the integrity check to purely read-only
    chains where no execution was ever attempted — those chains can produce
    correct answers from file reads and code inspection without running any
    commands, and blocking them wastes correct answers.
    """
    return any(
        (out or "").lstrip().lower().startswith(_EXEC_OUTPUT_PREFIX)
        for out in outputs
    )

_PACKAGE_NAME_BY_IMPORT = {
    "Bio": "biopython",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "esm": "fair-esm",
    "sklearn": "scikit-learn",
    "torch_geometric": "torch-geometric",
    "yaml": "pyyaml",
}


class ToolOutputCapture(RunHooks[ResearchContext]):
    """Record actual tool outputs in the order the SDK observes them."""

    def __init__(self) -> None:
        self.outputs: list[str] = []

    async def on_tool_end(self, context: Any, agent: Any, tool: Any, result: str) -> None:
        """Store the real tool result for later chain validation."""
        self.outputs.append(str(result))


@dataclass
class InstallEvent:
    """Record one deterministic dependency-install attempt."""

    attempt: int
    modules: list[str]
    packages: list[str]
    command: list[str]
    exit_code: int
    output: str

    @property
    def succeeded(self) -> bool:
        """True when the install command completed successfully."""
        return self.exit_code == 0


@dataclass
class AgentUsage:
    """Token and cost accounting for one agent invocation.

    Stored per invocation rather than per unique role because some teams
    intentionally retry the worker or run the critic multiple times.  The
    saved JSON needs each call preserved so total spend can be audited
    against the actual orchestration path, not an averaged summary.
    """

    stage: str
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    attempt: int | None = None

    @property
    def total_tokens(self) -> int:
        """Return total tokens consumed by this invocation."""
        return self.input_tokens + self.output_tokens


def usage_from_result(
    result: Any,
    *,
    stage: str,
    agent_name: str,
    model: str,
    attempt: int | None = None,
) -> AgentUsage:
    """Extract one ``AgentUsage`` record from a Runner result object.

    Kept tolerant of missing usage fields so unit tests can supply small
    ``SimpleNamespace`` fixtures without reproducing the SDK's full result
    shape.  Production runs always provide the real usage numbers.
    """
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return AgentUsage(
        stage=stage,
        agent_name=agent_name,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        attempt=attempt,
    )


@dataclass
class TeamRunResult:
    """Result bundle returned by worker plus critic orchestration."""

    answer: ReActAnswer
    worker_result: Any
    captures: list[ToolOutputCapture] = field(default_factory=list)
    reviews: list[CriticReview] = field(default_factory=list)
    install_events: list[InstallEvent] = field(default_factory=list)
    # Optional structured extraction payload for teams that separate paper
    # and repo understanding into a dedicated first stage.
    extraction_report: dict[str, Any] | None = None
    # Optional per-team structured payload persisted into the final run
    # JSON.  Most teams leave this as None; the workflow-testing team uses
    # it to expose the TestingReport that would otherwise only exist in
    # memory and in the worker prompt preamble.
    testing_report: dict[str, Any] | None = None
    # Optional post-execution discrepancy analysis payload. Kept separate
    # from the worker answer because a blocked benchmark answer and a
    # reproducibility-gap diagnosis are related but not interchangeable.
    gap_report: dict[str, Any] | None = None
    # Per-agent usage for every stage the team ran.  Stored at the team
    # boundary so ``react_main`` can write one consistent JSON schema for
    # single-agent, worker+critic, and multi-stage teams alike.
    agent_usages: list[AgentUsage] = field(default_factory=list)

    @property
    def final_capture(self) -> ToolOutputCapture:
        """Return the capture from the worker attempt that produced answer."""
        return self.captures[-1]


def _package_for_import(import_name: str) -> str:
    """Map an import name from a traceback to a pip-installable package name."""
    if any(marker in import_name for marker in ("==", ">=", "<=", "~=", "!=")):
        return import_name
    top_level = import_name.split(".", maxsplit=1)[0]
    return _PACKAGE_NAME_BY_IMPORT.get(top_level, top_level)


def _detect_missing_modules(outputs: list[str]) -> list[str]:
    """Extract unique missing import names from captured tool outputs."""
    seen: set[str] = set()
    missing: list[str] = []
    for output in outputs:
        for match in _MISSING_MODULE_RE.finditer(output):
            module = match.group(1).strip()
            if module and module not in seen:
                seen.add(module)
                missing.append(module)
    return missing


def _install_packages(context: ResearchContext, modules: list[str], attempt: int) -> InstallEvent:
    """Install missing modules into the shared per-paper venv.

    Returns an InstallEvent instead of raising on pip failure so the caller
    can include the failed install in the final JSON and avoid a blind retry.
    """
    packages = [_package_for_import(module) for module in modules]
    python_exe = _find_python_in_venv(context.venv_path)
    if python_exe is None:
        return InstallEvent(
            attempt=attempt,
            modules=modules,
            packages=packages,
            command=[],
            exit_code=1,
            output=f"No Python interpreter found in venv: {context.venv_path}",
        )

    command = ["uv", "pip", "install", "--python", str(python_exe), *packages]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=MAX_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else exc.stdout
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else exc.stderr
        )
        output = "\n".join(part for part in [stdout, stderr] if part)
        return InstallEvent(
            attempt=attempt,
            modules=modules,
            packages=packages,
            command=command,
            exit_code=124,
            output=f"Install timed out after {MAX_TIMEOUT} seconds.\n{output}".strip(),
        )

    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    return InstallEvent(
        attempt=attempt,
        modules=modules,
        packages=packages,
        command=command,
        exit_code=result.returncode,
        output=output.strip(),
    )


def _truncate_for_review(text: str, limit: int = 5000) -> str:
    """Cap long tool outputs before sending them to the critic."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[truncated at {limit} chars]"


def _build_critic_input(
    question: str,
    ground_truth: str | None,
    answer: ReActAnswer,
    tool_outputs: list[str],
    install_events: list[InstallEvent] | None = None,
) -> str:
    """Serialize worker evidence into a critic-readable prompt."""
    payload = {
        "question": question,
        "ground_truth": ground_truth or "",
        "worker_answer": json.loads(answer.model_dump_json()),
        "captured_tool_outputs": [
            {"index": i + 1, "output": _truncate_for_review(output)}
            for i, output in enumerate(tool_outputs)
        ],
        "install_events": [
            {
                "attempt": event.attempt,
                "modules": event.modules,
                "packages": event.packages,
                "exit_code": event.exit_code,
                "output": _truncate_for_review(event.output),
            }
            for event in install_events or []
        ],
    }
    return (
        "Review this worker attempt for benchmark integrity. "
        "Return only the structured CriticReview.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )


def run_with_critic(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    worker_model: str,
    critic_model: str = DEFAULT_MODEL,
    max_retries: int = 1,
    worker_factory: WorkerFactory = create_react_agent,
    needs_execution: bool = False,
) -> TeamRunResult:
    """Run worker, review with critic, and optionally retry once.

    ``worker_factory`` defaults to the baseline ``create_react_agent`` so
    existing callers (and the colleague's ``worker-critic`` team) keep
    their exact behavior.  The ``worker-critic-plus`` team supplies
    ``create_react_agent_improved`` here to swap in the improved-variant
    prompt without forking the orchestration logic.
    """
    reviews: list[CriticReview] = []
    captures: list[ToolOutputCapture] = []
    install_events: list[InstallEvent] = []
    agent_usages: list[AgentUsage] = []
    feedback_for_retry = ""

    last_answer: ReActAnswer | None = None
    last_worker_result: Any = None

    for attempt_index in range(max_retries + 1):
        worker = worker_factory(worker_model)
        capture = ToolOutputCapture()
        worker_input = question
        if feedback_for_retry:
            worker_input = f"{question}\n\n[RETRY HINT] {feedback_for_retry}"

        worker_result = Runner.run_sync(
            worker,
            worker_input,
            context=context,
            max_turns=150,
            hooks=capture,
        )
        agent_usages.append(
            usage_from_result(
                worker_result,
                stage="execution_worker",
                agent_name=getattr(worker, "name", "Execution worker"),
                model=worker_model,
                attempt=attempt_index + 1,
            )
        )
        captures.append(capture)
        answer = worker_result.final_output
        last_answer = answer
        last_worker_result = worker_result

        missing = _detect_missing_modules(capture.outputs)
        if missing and attempt_index < max_retries:
            install_event = _install_packages(context, missing, attempt=attempt_index + 1)
            install_events.append(install_event)
            if install_event.succeeded:
                feedback_for_retry = (
                    f"Packages {install_event.packages} are now installed in the shared venv. "
                    "Re-run the failed command and continue from the real output."
                )
                continue

        critic = create_critic_agent(model=critic_model)
        critic_input = _build_critic_input(
            question=question,
            ground_truth=ground_truth,
            answer=answer,
            tool_outputs=capture.outputs,
            install_events=install_events,
        )
        critic_result = Runner.run_sync(
            critic,
            critic_input,
            context=context,
            max_turns=10,
        )
        agent_usages.append(
            usage_from_result(
                critic_result,
                stage="critic_review",
                agent_name=getattr(critic, "name", "Critic"),
                model=critic_model,
                attempt=len(reviews) + 1,
            )
        )
        review = critic_result.final_output
        reviews.append(review)

        if review.verdict in {"pass", "incorrect"} or attempt_index >= max_retries:
            break

        if review.verdict == "redo_with_install" and review.missing_packages:
            install_event = _install_packages(
                context,
                review.missing_packages,
                attempt=attempt_index + 1,
            )
            install_events.append(install_event)
            if not install_event.succeeded:
                break
            feedback_for_retry = (
                review.suggested_action
                or f"Packages {install_event.packages} are now installed. Retry execution."
            )
            continue

        if review.verdict in {"redo_more_steps", "redo_with_search"}:
            feedback_for_retry = review.suggested_action or review.reasoning
            continue

        break

    if last_answer is None or last_worker_result is None:
        raise RuntimeError(f"No worker result produced for {entry_id}")

    # Only activate the guard when execution was actually attempted. If the
    # worker answered from reads alone (file listings, code inspection) the
    # guard would incorrectly downgrade correct read-derived answers because
    # no execute_command ever ran.  needs_execution=True from the caller says
    # "this *kind* of question needs execution"; the auto-detect adds "AND
    # the agent actually tried to run something this time."
    effective_needs_execution = needs_execution and _execution_was_attempted(
        captures[-1].outputs
    )
    guarded = apply_integrity_guard(
        last_answer, captures[-1].outputs, needs_execution=effective_needs_execution
    )
    return TeamRunResult(
        answer=guarded,
        worker_result=last_worker_result,
        captures=captures,
        reviews=reviews,
        install_events=install_events,
        agent_usages=agent_usages,
    )
