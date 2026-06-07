"""Gate agent for answer validation against detected reproducibility gaps.

This is the sixth and final stage of the testing-worker-critic pipeline.
It receives the worker's final answer alongside the gap detection report and
decides whether the answer should stand, be flagged as uncertain, or be
overridden with an EXECUTION_REQUIRED block.

The key judgement the gate makes that a deterministic rule cannot: did the
worker *validly bypass* the gap (e.g. rewrote a broken script and got the
right answer independently), or was the worker *fooled* by the gap (e.g.
read a poisoned artifact and returned its value confidently)?  A bypass
should pass; being fooled should block.
"""

import json
from typing import Any, Literal

from agents import Agent
from pydantic import BaseModel, Field

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext


class GateDecision(BaseModel):
    """Structured verdict from the gate stage."""

    # Three-way outcome drives how the answer is modified before saving.
    verdict: Literal["pass", "block", "warn"] = Field(
        description=(
            "pass — answer is reliable despite gaps; "
            "block — a critical gap directly invalidates the answer; "
            "warn — gaps raise uncertainty but the answer may still be useful."
        )
    )

    # Single sentence — appears in the modified answer when verdict != pass.
    reasoning: str = Field(
        description="One-sentence explanation of why this verdict was chosen."
    )

    # Which gap titles drove the decision; empty for pass verdicts.
    triggered_gaps: list[str] = Field(
        default_factory=list,
        description="Titles of gaps from the gap_report that drove this verdict.",
    )


def build_gate_input(
    *,
    question: str,
    final_answer: str,
    answer_status: str,
    gap_report: dict[str, Any],
) -> str:
    """Serialize the answer and gap evidence for the gate agent.

    Keeps the payload small: the gate only needs the answer and the
    gap titles/types/severities, not the full execution tool outputs
    that the gap detector already processed.
    """
    slim_gaps = [
        {
            "title": g.get("title", ""),
            "gap_type": g.get("gap_type", ""),
            "severity": g.get("severity", ""),
            "explanation": g.get("explanation", "")[:200],
        }
        for g in gap_report.get("identified_gaps", [])
    ]
    payload = {
        "question": question,
        "worker_answer": final_answer,
        "answer_status": answer_status,
        "overall_gap_assessment": gap_report.get("overall_gap_assessment", ""),
        "identified_gaps": slim_gaps,
    }
    return (
        "Review the worker answer against the detected gaps and return a GateDecision.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )


def apply_gate_verdict(answer_obj: Any, decision: GateDecision) -> Any:
    """Return a modified answer object reflecting the gate verdict.

    Only block and warn verdicts change the answer; pass leaves it untouched.
    The original answer is preserved in the blocker_explanation so the
    chain of custody is traceable.
    """
    if decision.verdict == "pass":
        return answer_obj

    gap_list = "; ".join(decision.triggered_gaps) if decision.triggered_gaps else "see gap report"

    if decision.verdict == "block":
        new_answer = f"EXECUTION_REQUIRED — gate blocked: {decision.reasoning} (gaps: {gap_list})"
        return answer_obj.model_copy(
            update={
                "final_answer": new_answer,
                "answer_status": "blocked",
                "blocker_type": "runtime_error",
                "blocker_explanation": (
                    f"Gate agent blocked this answer. {decision.reasoning} "
                    f"Original answer was: {answer_obj.final_answer}"
                ),
            }
        )

    # warn — keep answer but prepend uncertainty marker
    new_answer = f"[UNCERTAIN — {decision.reasoning}] {answer_obj.final_answer}"
    return answer_obj.model_copy(update={"final_answer": new_answer})


_GATE_INSTRUCTIONS = """\
You are the GATE AGENT. You receive a worker's final answer and a list of
reproducibility gaps detected in the paper/repo/execution. Your job is to
decide whether the answer should pass, be blocked, or carry a warning.

DECISION RULES
--------------
pass:
  - The worker validly bypassed any gaps (e.g. rewrote a broken script,
    computed the answer independently without relying on the broken artifact).
  - No high-severity gap directly undermines the specific value returned.
  - The answer is already EXECUTION_REQUIRED (nothing to override).

block:
  - A high-severity gap of type execution_gap, missing_artifact, or
    fragile_setup directly prevents reliable reproduction of the requested
    result AND the worker did not demonstrably bypass it.
  - The worker's answer is a concrete value but execution evidence shows
    the underlying workflow could not run correctly.

warn:
  - Gaps exist and raise uncertainty, but the worker may still have reached
    a valid answer through an alternative path.
  - Use warn when you cannot determine from the evidence whether the bypass
    was legitimate or whether the answer is coincidentally correct.

KEY DISTINCTION
---------------
A bypass is legitimate when the worker independently reproduced the result
(e.g. wrote and executed its own script). A bypass is NOT legitimate when
the worker read a pre-computed artifact that may itself be poisoned or
stale, without re-running the underlying computation.

Keep reasoning to one sentence. List only the gap titles that directly
drove your verdict in triggered_gaps; leave it empty for pass verdicts.
"""


def create_gate_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the lightweight gate agent with no tools."""
    return Agent(
        name="Gate Agent",
        instructions=_GATE_INSTRUCTIONS,
        tools=[],
        model=model,
        output_type=GateDecision,
    )
