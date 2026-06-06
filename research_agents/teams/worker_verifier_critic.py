"""worker-verifier-critic team: worker → code verifier → critic.

The verifier is inserted between the worker and critic. It checks a finite
bug checklist (ESM-2 BOS/EOS indexing, numpy 2.x aliases, pickle encoding,
FASTA counting, off-by-one after filtering, curl redirect failures) derived
from the annotation analysis of the 65-question compbio benchmark.

When the verifier finds and fixes a bug it re-executes the corrected script
in the existing workspace and the new result replaces the worker's answer
before the critic reviews it.  The critic then sees the corrected chain and
makes a final pass/fail decision.

Flow:
  worker → [optional: auto-install missing modules] → verifier → critic

The verifier fires on every run regardless of whether the worker succeeded.
This is intentional: the BOS/EOS bug passes the critic (the chain looks real)
but produces a wrong numeric answer — exactly the pattern the verifier targets.
"""

import json

from agents import Runner

from research_agents.agents.critic_agent import create_critic_agent
from research_agents.agents.react_agent import ReActAnswer, create_react_agent_improved
from research_agents.agents.verifier_agent import VerifierReview, create_verifier_agent
from research_agents.config import DEFAULT_MODEL
from research_agents.orchestration import (
    InstallEvent,
    TeamRunResult,
    ToolOutputCapture,
    _build_critic_input,
    _detect_missing_modules,
    _install_packages,
    _truncate_for_review,
)
from research_agents.project import ResearchContext


# ---------------------------------------------------------------------------
# Verifier input builder
# ---------------------------------------------------------------------------


def _extract_scripts_from_chain(answer: ReActAnswer) -> list[dict]:
    """Pull write_file calls out of the chain so the verifier can see what was written.

    The action field of each ReActStep contains the tool call as a string,
    e.g. 'write_file(relative_path="fix.py", content="import numpy...")'.
    We extract steps that reference write_file so the verifier can see both
    the script content and the step number where it was written.
    """
    scripts = []
    for step in answer.chain:
        action = step.action or ""
        if "write_file" in action.lower():
            scripts.append({
                "step": step.step,
                "action": _truncate_for_review(action, limit=3000),
                "observation": _truncate_for_review(step.observation or "", limit=500),
            })
    return scripts


def _extract_exec_outputs(tool_outputs: list[str]) -> list[dict]:
    """Pull execute_command results from captured outputs.

    The integrity guard already filters by 'exit code:' prefix; we do the
    same here so the verifier sees real stdout/stderr rather than paper reads.
    """
    return [
        {"index": i + 1, "output": _truncate_for_review(out, limit=1500)}
        for i, out in enumerate(tool_outputs)
        if "exit code" in (out or "").lower()
    ]


def _build_verifier_input(
    question: str,
    ground_truth: str | None,
    answer: ReActAnswer,
    tool_outputs: list[str],
) -> str:
    """Serialize the worker's scripts and execution history for the verifier."""
    payload = {
        "question": question,
        "ground_truth": ground_truth or "",
        "worker_final_answer": answer.final_answer,
        "answer_status": answer.answer_status,
        # Scripts written during the chain — the verifier rewrites these.
        "scripts_written_by_worker": _extract_scripts_from_chain(answer),
        # Real execution outputs — the verifier checks for error patterns.
        "execution_outputs": _extract_exec_outputs(tool_outputs),
    }
    return (
        "Check the worker's scripts against your bug checklist. "
        "Re-execute in the workspace if you find a fixable bug.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )


def _announce_stage(stage_name: str) -> None:
    """Print a short stage marker so verifier runs expose the active agent."""
    print(f"[team/worker-verifier-critic] {stage_name}...")


# ---------------------------------------------------------------------------
# Team run function
# ---------------------------------------------------------------------------


def run_worker_verifier_critic(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str = DEFAULT_MODEL,
) -> TeamRunResult:
    """Run worker → verifier → critic with one optional dependency-install retry.

    The verifier runs even when the worker's answer_status is 'blocked' —
    some blocked answers are caused by the numpy 2.x alias bug or a curl
    redirect failure that the verifier can fix, allowing re-execution to
    succeed.  The verifier skips immediately when the answer is a bare
    EXECUTION_REQUIRED with no scripts written.
    """
    install_events: list[InstallEvent] = []
    all_captures: list[ToolOutputCapture] = []

    # ── Stage 1: worker ───────────────────────────────────────────────────
    worker = create_react_agent_improved(model=model)
    capture = ToolOutputCapture()
    _announce_stage("Execution worker")
    worker_result = Runner.run_sync(
        worker,
        question,
        context=context,
        max_turns=150,
        hooks=capture,
    )
    all_captures.append(capture)
    answer: ReActAnswer = worker_result.final_output

    # ── Optional: deterministic missing-module install + one retry ────────
    # Same behaviour as worker-critic: if the captured outputs contain a
    # ModuleNotFoundError we install and retry before the verifier runs,
    # so the verifier sees the result of a successful (or at least further)
    # execution attempt.
    missing = _detect_missing_modules(capture.outputs)
    if missing:
        _announce_stage("Dependency install retry 1")
        install_event = _install_packages(context, missing, attempt=1)
        install_events.append(install_event)
        if install_event.succeeded:
            retry_capture = ToolOutputCapture()
            _announce_stage("Execution worker retry 1")
            retry_result = Runner.run_sync(
                worker,
                question,
                context=context,
                max_turns=150,
                hooks=retry_capture,
            )
            all_captures.append(retry_capture)
            worker_result = retry_result
            answer = retry_result.final_output
            capture = retry_capture   # verifier + critic see the retry outputs

    # ── Stage 2: verifier ─────────────────────────────────────────────────
    verifier = create_verifier_agent(model=model)
    verifier_input = _build_verifier_input(question, ground_truth, answer, capture.outputs)
    _announce_stage("Verifier review")
    verifier_result = Runner.run_sync(
        verifier,
        verifier_input,
        context=context,
        max_turns=30,       # narrow task — 30 turns is generous
    )
    verifier_review: VerifierReview = verifier_result.final_output

    # Apply the verifier's corrected answer when it fixed a bug.
    # model_copy creates a new Pydantic model instance with the updated field;
    # the rest of the answer (chain, blocker fields, etc.) is unchanged so the
    # critic can still audit the full chain.
    if verifier_review.verdict == "bug_found_fixed" and verifier_review.corrected_answer:
        answer = answer.model_copy(
            update={
                "final_answer": verifier_review.corrected_answer,
                "answer_status": "answered",
                "blocker_type": "none",
            }
        )

    # ── Stage 3: critic ───────────────────────────────────────────────────
    critic = create_critic_agent(model=model)
    critic_input = _build_critic_input(
        question=question,
        ground_truth=ground_truth,
        answer=answer,
        tool_outputs=capture.outputs,
        install_events=install_events,
    )
    _announce_stage("Critic review")
    critic_review = Runner.run_sync(
        critic,
        critic_input,
        context=context,
        max_turns=10,
    ).final_output

    # Attach the verifier review to the reviews list so it appears in the
    # saved chain JSON.  The review is prepended (before the critic) so the
    # audit trail reads: worker → verifier → critic.
    all_reviews = [verifier_review, critic_review]

    return TeamRunResult(
        answer=answer,
        worker_result=worker_result,
        captures=all_captures,
        reviews=all_reviews,
        install_events=install_events,
    )
