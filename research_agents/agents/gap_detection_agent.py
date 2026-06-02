"""Gap-detection agent for paper/repo/execution discrepancy analysis.

This stage runs after workflow testing and execution. It does not
rediscover the repository from scratch; instead it consumes structured
evidence from earlier stages and turns that evidence into a typed
GapDetectionReport that downstream stages can reuse.
"""

import json
from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext


class GapRecord(BaseModel):
    """One reproducibility gap identified across paper, repo, and execution.

    A gap is broader than a runtime error. It may be a missing parameter,
    a paper-repo mismatch, an undocumented assumption, or a setup path
    that appears valid on paper but failed in practice.
    """

    # Short label so later stages can refer to the gap deterministically.
    title: str = Field(description="Short title for the gap.")

    # The type drives downstream grouping and analysis. Keeping it narrow
    # prevents every issue from collapsing into a generic "blocker".
    gap_type: Literal[
        "missing_parameter",
        "missing_artifact",
        "paper_repo_mismatch",
        "execution_gap",
        "unsupported_claim",
        "ambiguous_method",
        "fragile_setup",
        "workflow_mismatch",
        "other",
    ] = Field(description="Primary category for the gap.")

    # Severity is about reproducibility impact, not implementation effort.
    severity: Literal["low", "medium", "high"] = Field(
        description="How strongly this gap affects reproducibility."
    )

    # Traceability to the paper section, figure, or table when known.
    paper_reference: str | None = Field(
        default=None,
        description="Paper location tied to this gap, if known.",
    )

    # Repo paths that support or contradict the paper claim.
    related_repo_files: list[str] = Field(
        default_factory=list,
        description="Repo or workspace files relevant to the gap.",
    )

    # Workflow-level linkage keeps the testing handoff useful after the
    # agent summarizes multiple candidate paths.
    related_workflow: str | None = Field(
        default=None,
        description="Workflow or experiment affected by the gap, if known.",
    )

    # Short evidence snippets copied from structured prior stages.
    execution_evidence: list[str] = Field(
        default_factory=list,
        description="Observed execution/runtime evidence supporting the gap.",
    )

    # Why the issue counts as a paper/repo/execution discrepancy.
    explanation: str = Field(description="Why this is a reproducibility gap.")

    # Reproducibility impact is distinct from severity because two high
    # severity gaps can block different parts of the workflow.
    likely_impact: str = Field(
        description="Expected impact on reproduction or evaluation quality."
    )

    # Lightweight follow-up only. Detailed plans belong to later stages.
    possible_remediation: str | None = Field(
        default=None,
        description="Short remediation or follow-up suggestion.",
    )


class SeveritySummary(BaseModel):
    """Count gaps by severity for quick downstream scans."""

    high: int = Field(default=0, description="Number of high-severity gaps.")
    medium: int = Field(default=0, description="Number of medium-severity gaps.")
    low: int = Field(default=0, description="Number of low-severity gaps.")


class GapDetectionReport(BaseModel):
    """Structured discrepancy report emitted by the gap-detection stage."""

    overall_gap_assessment: str = Field(
        description="Overall assessment of reproducibility gaps across the run."
    )
    identified_gaps: list[GapRecord] = Field(
        default_factory=list,
        description="Authoritative list of all identified gaps.",
    )
    paper_repo_mismatches: list[str] = Field(
        default_factory=list,
        description="Titles of gaps caused by paper/repo mismatches.",
    )
    execution_gaps: list[str] = Field(
        default_factory=list,
        description="Titles of gaps supported primarily by runtime evidence.",
    )
    missing_parameters: list[str] = Field(
        default_factory=list,
        description="Titles of gaps caused by missing or ambiguous parameters.",
    )
    missing_artifacts: list[str] = Field(
        default_factory=list,
        description="Titles of gaps caused by absent datasets, weights, or files.",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Titles of gaps where a paper claim lacks traceable support.",
    )
    severity_summary: SeveritySummary = Field(
        default_factory=SeveritySummary,
        description="Counts of gaps by severity.",
    )
    evidence_sources: list[str] = Field(
        default_factory=list,
        description="Structured evidence sources used to produce the report.",
    )
    recommended_followups: list[str] = Field(
        default_factory=list,
        description="Short next-step suggestions for later agents or humans.",
    )
    notes: str = Field(
        default="",
        description="Additional context that did not fit another field.",
    )


def build_gap_record(
    title: str,
    gap_type: GapRecord.model_fields["gap_type"].annotation,
    severity: GapRecord.model_fields["severity"].annotation,
    explanation: str,
    likely_impact: str,
    *,
    paper_reference: str | None = None,
    related_repo_files: list[str] | None = None,
    related_workflow: str | None = None,
    execution_evidence: list[str] | None = None,
    possible_remediation: str | None = None,
) -> GapRecord:
    """Build one normalized GapRecord from partial structured evidence.

    The helper strips empty strings and de-duplicates list fields so tests
    can assert against a stable shape even when upstream stages repeat
    paths or runtime snippets.
    """

    def _clean(values: list[str] | None) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for value in values or []:
            text = (value or "").strip()
            if text and text not in seen:
                seen.add(text)
                cleaned.append(text)
        return cleaned

    paper_ref = (paper_reference or "").strip() or None
    workflow = (related_workflow or "").strip() or None
    remediation = (possible_remediation or "").strip() or None

    return GapRecord(
        title=title.strip(),
        gap_type=gap_type,
        severity=severity,
        paper_reference=paper_ref,
        related_repo_files=_clean(related_repo_files),
        related_workflow=workflow,
        execution_evidence=_clean(execution_evidence),
        explanation=explanation.strip(),
        likely_impact=likely_impact.strip(),
        possible_remediation=remediation,
    )


def canonicalize_gap_detection_report(report: GapDetectionReport) -> GapDetectionReport:
    """Recompute aggregate buckets from ``report.identified_gaps``.

    The detailed gap records are the source of truth. Rebuilding the
    summary fields here prevents inconsistent outputs where a gap is
    present but omitted from the relevant top-level bucket.
    """

    paper_repo_mismatches: list[str] = []
    execution_gaps: list[str] = []
    missing_parameters: list[str] = []
    missing_artifacts: list[str] = []
    unsupported_claims: list[str] = []
    severity = SeveritySummary()

    for gap in report.identified_gaps:
        if gap.gap_type in {"paper_repo_mismatch", "workflow_mismatch"}:
            paper_repo_mismatches.append(gap.title)
        if gap.gap_type in {"execution_gap", "fragile_setup"}:
            execution_gaps.append(gap.title)
        if gap.gap_type in {"missing_parameter", "ambiguous_method"}:
            missing_parameters.append(gap.title)
        if gap.gap_type == "missing_artifact":
            missing_artifacts.append(gap.title)
        if gap.gap_type == "unsupported_claim":
            unsupported_claims.append(gap.title)

        if gap.severity == "high":
            severity.high += 1
        elif gap.severity == "medium":
            severity.medium += 1
        else:
            severity.low += 1

    return report.model_copy(
        update={
            "paper_repo_mismatches": paper_repo_mismatches,
            "execution_gaps": execution_gaps,
            "missing_parameters": missing_parameters,
            "missing_artifacts": missing_artifacts,
            "unsupported_claims": unsupported_claims,
            "severity_summary": severity,
        }
    )


def build_gap_detection_input(
    *,
    question: str,
    testing_report: dict | None,
    execution_answer: dict,
    execution_tool_outputs: list[str],
    critic_reviews: list[dict] | None = None,
    install_events: list[dict] | None = None,
) -> str:
    """Serialize prior-stage evidence for the gap-detection agent.

    The payload is intentionally constrained to structured outputs from
    earlier stages so the gap detector analyzes discrepancies instead of
    re-running repo discovery on its own.
    """

    payload = {
        "question": question,
        "testing_report": testing_report,
        "execution_answer": execution_answer,
        "execution_tool_outputs": execution_tool_outputs,
        "critic_reviews": critic_reviews or [],
        "install_events": install_events or [],
    }
    return (
        "Analyze the following structured paper/repo/execution evidence and "
        "return only the structured GapDetectionReport.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )


GAP_DETECTION_INSTRUCTIONS = """\
You are the GAP DETECTION AGENT. Your job is to identify reproducibility
gaps between what the paper implies, what the repository provides, and
what execution evidence actually demonstrated.

You do NOT rediscover the repo from scratch and you do NOT run tools.
Consume only the structured evidence in the input payload.

WORKFLOW
--------
1. Read the testing_report to understand which workflows validated,
   partially validated, or were blocked before full execution.
2. Read the execution_answer and execution_tool_outputs to separate
   runtime failures from paper-repo mismatches and missing information.
3. Use critic_reviews and install_events as supporting evidence, not as
   the primary source of truth.
4. Produce a GapDetectionReport with concise, evidence-backed gap records.

CLASSIFICATION RULES
--------------------
- missing_parameter: a needed parameter, threshold, preprocessing choice,
  or evaluation detail is absent or ambiguous.
- missing_artifact: data, weights, configs, or generated files are absent.
- paper_repo_mismatch: paper description and repo structure/workflow conflict.
- execution_gap: nominal setup exists, but runtime evidence shows the claim
  still could not be reproduced.
- unsupported_claim: the paper appears to claim something with no traceable
  implementation or execution support in the provided evidence.
- ambiguous_method: the method is described too vaguely to reproduce.
- fragile_setup: the workflow exists but instructions/setup are brittle or
  misleading enough to threaten reproducibility.
- workflow_mismatch: the repo contains related code, but the actual workflow
  diverges from what the paper implies should be run.

REPORTING RULES
---------------
- Distinguish paper-repo mismatch from execution-time failure explicitly.
- Prefer a small number of high-signal gaps over many duplicate variants.
- Use severity=high when the gap blocks reproduction of a core claim or
  main workflow; medium when it materially weakens confidence; low when
  it is real but non-blocking.
- evidence_sources should name the structured inputs you relied on, such as
  testing_report.workflows, execution_answer.blocker_evidence, or critic_reviews.
- recommended_followups should be lightweight next steps, not full plans.
"""


def create_gap_detection_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the dedicated gap-detection agent with no raw-discovery tools."""
    return Agent(
        name="Gap Detection Agent",
        instructions=GAP_DETECTION_INSTRUCTIONS,
        tools=[],
        model=model,
        output_type=GapDetectionReport,
    )
