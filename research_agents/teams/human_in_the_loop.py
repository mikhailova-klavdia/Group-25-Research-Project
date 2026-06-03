"""Three-stage human-in-the-loop team: triage → (read-only answer | setup → execution).

Stage 0 — a **Repo Scout** reads the paper + explores the repo and decides whether the
question needs code execution. Read-only questions ("summarise this paper", "what is this
repo about") are answered straight from the paper/repo text — **no venv setup, no critic**.
Questions that need execution go through the **setup engineer** (which prepares the venv
interactively — no config file) and then the reused **worker + critic** loop, finished by a
deterministic **integrity guard** that downgrades an "answered" result not backed by any
successful command (the "answered without really running it" failure mode).

Every stage shares one ``ResearchContext``, so ``ask_human`` and the optional progress
``reporter`` work throughout. On a headless/batch run both are ``None``, so the team still
completes autonomously and silently — safe to select from ``react_main`` too.
"""

from typing import Any

from agents import Runner

from research_agents.agents.hitl_agents import (
    EnvReport,
    TriageReport,
    create_execution_agent_hitl,
    create_readonly_agent,
    create_setup_agent,
    create_triage_agent,
    format_env_report_for_worker,
    format_triage_for_downstream,
)
from research_agents.hitl import apply_integrity_guard
from research_agents.orchestration import (
    AgentUsage,
    TeamRunResult,
    ToolOutputCapture,
    run_with_critic,
    usage_from_result,
)
from research_agents.project import ResearchContext


# Friendly labels for live tool-level progress — only shown when a reporter is
# attached (i.e. the interactive CLI); silent otherwise.
_TOOL_LABELS = {
    "read_paper": "reading the paper",
    "list_repo_files": "scanning the repo",
    "find_repo_files": "searching the repo",
    "search_repo": "searching the repo",
    "read_repo_file": "reading a repo file",
    "resolve_repo_path": "locating a file",
    "write_file": "writing a script",
    "stage_repo_path": "staging files into the workspace",
    "execute_command": "running a command",
    "list_workspace_files": "checking the workspace",
    "read_workspace_file": "reading an output file",
    "list_paper_artifacts": "checking cached artifacts",
    "stage_paper_artifact": "reusing a cached artifact",
    "cache_workspace_artifact": "caching an output",
    "venv_status": "checking the environment",
    "ask_human": "asking you",
}


class ReportingCapture(ToolOutputCapture):
    """Captures tool outputs (as the base does) AND reports each tool call to a reporter.

    Used only for the team-controlled stages (triage / setup / read-only); the execution
    stage runs through ``run_with_critic``, which owns its own plain capture, so that stage
    is announced at the stage level instead of per tool.
    """

    def __init__(self, reporter: Any | None) -> None:
        super().__init__()
        self._reporter = reporter

    async def on_tool_start(self, context: Any, agent: Any, tool: Any) -> None:
        """Emit a friendly 'doing X…' line before each tool runs."""
        if self._reporter is not None:
            name = getattr(tool, "name", "") or ""
            self._reporter.detail(_TOOL_LABELS.get(name, f"using {name}" if name else "working…"))


def _capture(context: ResearchContext) -> ToolOutputCapture:
    """A ``ReportingCapture`` when a reporter is attached, else a plain capture."""
    reporter = getattr(context, "reporter", None)
    return ReportingCapture(reporter) if reporter is not None else ToolOutputCapture()


def _stage(context: ResearchContext, message: str) -> None:
    """Announce a high-level stage if a reporter is attached (no-op otherwise)."""
    reporter = getattr(context, "reporter", None)
    if reporter is not None:
        reporter.stage(message)


def _run_triage_stage(
    context: ResearchContext, question: str, model: str
) -> tuple[TriageReport, ToolOutputCapture, AgentUsage]:
    """Stage 0 — the Repo Scout classifies the question and maps the repo.

    If ``context.session_overview`` is already set (a previous question in the
    same hitl_main session already explored the repo), it is injected into the
    triage input so the scout skips re-reading the paper and only finds paths
    relevant to THIS question.  After the first successful triage the overview is
    written back to ``context.session_overview`` so hitl_main can propagate it
    to subsequent fresh workspaces.
    """
    cached = context.session_overview
    if cached:
        _stage(context, "Deciding how to approach your question (repo already explored)…")
        triage_input = (
            f"REPO OVERVIEW (already gathered — use this, skip read_paper()):\n"
            f"{cached}\n\n"
            f"Question to triage:\n{question}"
        )
    else:
        _stage(context, "Reading the paper and scanning the repo to understand your question…")
        triage_input = f"Question to triage:\n{question}"

    capture = _capture(context)
    result = Runner.run_sync(
        create_triage_agent(model),
        triage_input,
        context=context,
        max_turns=150,
        hooks=capture,
    )
    triage: TriageReport = result.final_output

    # Write the overview back so hitl_main can cache it across questions.
    if context.session_overview is None and triage.repo_overview:
        context.session_overview = triage.repo_overview

    return triage, capture, usage_from_result(
        result,
        stage="triage",
        agent_name="Repo Scout",
        model=model,
    )


def _run_readonly_stage(
    context: ResearchContext, question: str, triage: TriageReport, model: str
) -> tuple[Any, ToolOutputCapture, AgentUsage]:
    """Stage R — answer a read-only question from the paper/repo text (no setup, no critic)."""
    _stage(context, "This doesn't need any code — answering from the paper and repo…")
    capture = _capture(context)
    answer_input = f"{format_triage_for_downstream(triage)}\n\nQUESTION:\n{question}"
    result = Runner.run_sync(
        create_readonly_agent(model),
        answer_input,
        context=context,
        max_turns=150,
        hooks=capture,
    )
    return result, capture, usage_from_result(
        result,
        stage="read_only_answer",
        agent_name="Read-only Answerer",
        model=model,
    )


def _run_setup_stage(
    context: ResearchContext, question: str, triage: TriageReport, model: str
) -> tuple[EnvReport, list[ToolOutputCapture], list[AgentUsage]]:
    """Stage 1 — the setup engineer prepares the venv (one retry if it reports not ready)."""
    _stage(context, "This needs code — setting up the environment (this can take a few minutes)…")
    setup_input = (
        f"{format_triage_for_downstream(triage)}\n\n"
        "Prepare the shared per-paper virtual environment so the paper's code can run. Do "
        "NOT answer the question itself — a separate execution agent will. The question the "
        f"environment must support is:\n\n{question}"
    )

    first_capture = _capture(context)
    result = Runner.run_sync(
        create_setup_agent(model), setup_input, context=context, max_turns=150, hooks=first_capture
    )
    usages = [
        usage_from_result(
            result,
            stage="setup",
            agent_name="Environment Setup Engineer",
            model=model,
            attempt=1,
        )
    ]
    env: EnvReport = result.final_output
    captures = [first_capture]

    if not env.venv_ready:
        _stage(context, "Setup hit a snag — trying once more to get the environment ready…")
        retry_capture = _capture(context)
        nudge = (
            f"{setup_input}\n\n[SETUP RETRY] Your previous attempt reported venv_ready=false "
            f"with known gaps: {env.known_gaps}. Resolve what you can now (call ask_human if a "
            "person is needed to unblock you) and return an updated EnvReport."
        )
        retry_result = Runner.run_sync(
            create_setup_agent(model), nudge, context=context, max_turns=150, hooks=retry_capture
        )
        usages.append(
            usage_from_result(
                retry_result,
                stage="setup",
                agent_name="Environment Setup Engineer",
                model=model,
                attempt=2,
            )
        )
        env = retry_result.final_output
        captures.append(retry_capture)

    return env, captures, usages


def run_human_in_the_loop(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Triage the question, then answer read-only directly or run setup → execution.

    Signature matches every other team's ``run`` so the CLI dispatchers
    (``react_main`` batch mode and the interactive ``hitl_main``) invoke it uniformly.
    """
    triage, triage_capture, triage_usage = _run_triage_stage(context, question, model)

    # ---- Read-only path: skip setup + critic entirely ----
    if not triage.needs_execution:
        readonly_result, readonly_capture, readonly_usage = _run_readonly_stage(
            context, question, triage, model
        )
        _stage(context, "Done.")
        return TeamRunResult(
            answer=readonly_result.final_output,
            worker_result=readonly_result,
            captures=[triage_capture, readonly_capture],
            reviews=[],
            install_events=[],
            agent_usages=[triage_usage, readonly_usage],
        )

    # ---- Execution path: setup → reused worker+critic loop → integrity guard ----
    env, setup_captures, setup_usages = _run_setup_stage(context, question, triage, model)

    _stage(context, "Running it…")
    exec_input = (
        f"{format_triage_for_downstream(triage)}\n\n"
        f"{format_env_report_for_worker(env)}\n\nQUESTION:\n{question}"
    )
    exec_result = run_with_critic(
        context=context,
        question=exec_input,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_execution_agent_hitl,
    )

    _stage(context, "Reviewing the result…")
    guarded = apply_integrity_guard(
        exec_result.answer,
        exec_result.final_capture.outputs,
        needs_execution=True,
    )
    if guarded is not exec_result.answer:
        _stage(context, "Couldn't confirm this by actually running it — marking it unconfirmed.")
    _stage(context, "Done.")

    return TeamRunResult(
        answer=guarded,
        worker_result=exec_result.worker_result,
        captures=[triage_capture, *setup_captures, *exec_result.captures],
        reviews=exec_result.reviews,
        install_events=exec_result.install_events,
        agent_usages=[triage_usage, *setup_usages, *exec_result.agent_usages],
    )
