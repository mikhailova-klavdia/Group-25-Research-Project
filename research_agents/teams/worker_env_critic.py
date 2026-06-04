"""Worker-env-critic team: Environment Agent → worker → critic.

Inserts a dedicated Environment Agent stage before the ReAct worker so
environment preparation is a first-class pipeline step with a structured
output, rather than being split across project.py, orchestration.py, and
execution-time retry logic.

Flow:
  1. Environment Agent  — discovers dep files, installs packages,
                          verifies imports, returns EnvironmentReport
  2. ReAct worker       — receives EnvironmentReport as preamble so it
                          starts from a known baseline
  3. Critic             — reviews chain integrity as usual

The Environment Agent runs even when the worker is retried; the venv is
already warm on retry so the agent finishes quickly and the updated report
reflects any packages the worker installed in its first attempt.
"""

import json

from agents import Runner

from research_agents.agents.critic_agent import create_critic_agent
from research_agents.agents.environment_agent import (
    EnvironmentReport,
    create_environment_agent,
    format_environment_report_for_worker,
)
from research_agents.agents.react_agent import ReActAnswer, create_react_agent_plus_plus
from research_agents.config import DEFAULT_MODEL
from research_agents.orchestration import (
    InstallEvent,
    TeamRunResult,
    ToolOutputCapture,
    _build_critic_input,
    _detect_missing_modules,
    _install_packages,
)
from research_agents.project import ResearchContext


# ---------------------------------------------------------------------------
# Environment Agent runner
# ---------------------------------------------------------------------------


def _run_environment_agent(
    context: ResearchContext,
    question: str,
    model: str,
) -> tuple[EnvironmentReport, ToolOutputCapture]:
    """Run the Environment Agent and return its report + tool capture.

    The question is included so the agent knows which packages are likely
    relevant and can prioritise checking them in the verify phase.
    """
    env_agent = create_environment_agent(model=model)
    capture = ToolOutputCapture()

    result = Runner.run_sync(
        env_agent,
        # Give the agent just enough context to prioritise its work —
        # not the full question, to keep it focused on env preparation.
        f"Prepare the environment for this benchmark question:\n{question[:500]}",
        context=context,
        max_turns=50,        # generous but bounded: 40-call limit in instructions
        hooks=capture,
    )
    return result.final_output, capture


# ---------------------------------------------------------------------------
# Team run function
# ---------------------------------------------------------------------------


def run_worker_env_critic(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str = DEFAULT_MODEL,
) -> TeamRunResult:
    """Run Environment Agent → worker → critic with one dependency-install retry.

    Compared with ``run_worker_critic_plus_plus``, the key addition is a
    structured EnvironmentReport that the worker receives as a preamble.
    This means:
      * The worker never redundantly re-installs packages.
      * The saved chain includes a machine-readable env readiness record.
      * Blockers detected by the env agent are surfaced before execution,
        not mid-chain after wasting turns on doomed install attempts.
    """
    install_events: list[InstallEvent] = []
    all_captures: list[ToolOutputCapture] = []

    # ── Stage 1: Environment Agent ─────────────────────────────────────────
    env_report, env_capture = _run_environment_agent(context, question, model)
    all_captures.append(env_capture)

    # If the environment is hard-blocked, return early rather than firing
    # the worker into a guaranteed failure.  The EnvironmentReport itself
    # is returned as the answer so downstream scoring can see why.
    if env_report.status == "blocked" and env_report.blockers:
        blocker_str = "; ".join(env_report.blockers)
        # Build a minimal ReActAnswer so the orchestration layer has a
        # uniform object to record regardless of which stage produced it.
        blocked_answer = ReActAnswer(
            chain=[],
            final_answer=f"EXECUTION_REQUIRED — environment blocked: {blocker_str}",
            answer_status="blocked",
            blocker_type="missing_dependency",
            blocker_explanation=(
                f"Environment Agent reported hard blockers before execution: {blocker_str}"
            ),
            blocker_evidence=env_report.blockers,
        )
        return TeamRunResult(
            answer=blocked_answer,
            worker_result=None,           # no worker ran
            captures=all_captures,
            reviews=[],
            install_events=[],
        )

    # ── Stage 2: Worker (plus-plus prompt + env preamble) ──────────────────
    env_preamble = format_environment_report_for_worker(env_report)
    worker_input = f"{env_preamble}\n\nQUESTION:\n{question}"

    worker = create_react_agent_plus_plus(model=model)
    worker_capture = ToolOutputCapture()

    worker_result = Runner.run_sync(
        worker,
        worker_input,
        context=context,
        max_turns=150,
        hooks=worker_capture,
    )
    all_captures.append(worker_capture)
    answer: ReActAnswer = worker_result.final_output

    # ── Optional: deterministic missing-module install + one retry ─────────
    # Even with the env agent's preparation, the worker may discover a
    # package the env agent did not know to install (e.g. an obscure
    # import buried in a script the env agent never executed).  Handle
    # this the same way worker-critic does.
    missing = _detect_missing_modules(worker_capture.outputs)
    if missing:
        install_event = _install_packages(context, missing, attempt=1)
        install_events.append(install_event)
        if install_event.succeeded:
            retry_capture = ToolOutputCapture()
            hint = (
                f"{env_preamble}\n\n"
                f"[RETRY HINT] Packages {install_event.packages} were just installed. "
                "Re-run the failed command and continue.\n\n"
                f"QUESTION:\n{question}"
            )
            retry_result = Runner.run_sync(
                worker,
                hint,
                context=context,
                max_turns=150,
                hooks=retry_capture,
            )
            all_captures.append(retry_capture)
            worker_result = retry_result
            answer = retry_result.final_output

    # ── Stage 3: Critic ────────────────────────────────────────────────────
    # The critic sees the final worker chain; the env report is injected
    # into extra_context so the critic can factor in env readiness when
    # judging whether the worker had a fair environment to work in.
    critic = create_critic_agent(model=model)
    critic_input = _build_critic_input(
        question=question,
        ground_truth=ground_truth,
        answer=answer,
        tool_outputs=all_captures[-1].outputs,
        install_events=install_events,
    )
    # Prepend the env report as context for the critic.
    critic_input_with_env = (
        f"[Environment Agent report for this question]\n"
        f"{format_environment_report_for_worker(env_report)}\n\n"
        + critic_input
    )
    critic_review = Runner.run_sync(
        critic,
        critic_input_with_env,
        context=context,
        max_turns=10,
    ).final_output

    return TeamRunResult(
        answer=answer,
        worker_result=worker_result,
        captures=all_captures,
        reviews=[critic_review],
        install_events=install_events,
    )
