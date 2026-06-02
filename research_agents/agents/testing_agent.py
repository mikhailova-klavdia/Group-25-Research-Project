"""Testing agent for workflow validation before execution-time reasoning.

The testing stage sits between repo understanding and the existing ReAct
worker. It performs targeted smoke checks on one or more candidate
workflows, then emits a structured handoff describing what is runnable,
what is partially validated, and what is blocked. The downstream worker
uses that handoff to focus its budget on workflows that already have some
execution evidence behind them.

The project does not yet have a dedicated Extraction Agent, so this stage
supports a compatibility mode: if the prompt already includes structured
workflow definitions, the tester validates those directly; otherwise it
derives a small set of candidate workflows from the question plus repo
inspection and validates them.
"""

from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from research_agents.agents.react_agent import REACT_INSTRUCTIONS_IMPROVED, ReActAnswer
from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.exec_tools import (
    execute_command,
    list_paper_artifacts,
    list_workspace_files,
    read_workspace_file,
    stage_paper_artifact,
    stage_repo_path,
    venv_status,
    write_file,
)
from research_agents.tools.paper_tools import read_paper
from research_agents.tools.repo_tools import (
    find_repo_files,
    list_repo_files,
    read_repo_file,
    resolve_repo_path,
    search_repo,
)


class WorkflowValidation(BaseModel):
    """Validation result for one candidate workflow.

    The testing stage is intentionally workflow-centric rather than
    command-centric: downstream reasoning cares which paper/repo workflow
    is runnable, not merely whether one shell command exited zero.
    """

    # Human-readable name so later stages can refer back to a validated
    # workflow without re-parsing free-form notes.
    workflow_name: str = Field(description="Short label for the workflow under test.")

    # Distinguishes a fully usable workflow from a smoke-tested but still
    # risky one, and from genuinely blocked/failed paths.
    status: Literal["validated", "partial", "blocked", "failed"] = Field(
        description="Validation outcome for this workflow."
    )

    # Traceability back to the paper section/figure/table, when known.
    paper_reference: str | None = Field(
        default=None,
        description="Paper location this workflow corresponds to, if known.",
    )

    # Repo/workspace files the tester actually staged or inspected.
    files_staged: list[str] = Field(
        default_factory=list,
        description="Files or directories staged into workspace during validation.",
    )

    # Real commands executed while validating. These are reused by the
    # worker when a workflow already has a promising invocation pattern.
    commands_run: list[str] = Field(
        default_factory=list,
        description="Shell commands executed while validating this workflow.",
    )

    # Concise summaries of command output or artifact observations.
    observed_outputs: list[str] = Field(
        default_factory=list,
        description="Observed outputs or artifacts from validation.",
    )

    # Missing paths/data/weights/configs are separated from runtime errors
    # because the downstream worker handles them differently.
    missing_inputs: list[str] = Field(
        default_factory=list,
        description="Required inputs or files that were missing.",
    )

    # Dependency issues may be fixable by install/setup steps; keep them
    # explicit rather than burying them in a generic runtime error field.
    dependency_issues: list[str] = Field(
        default_factory=list,
        description="Dependency/import issues observed during validation.",
    )

    # Anything that failed after inputs and dependencies were available.
    runtime_errors: list[str] = Field(
        default_factory=list,
        description="Runtime/configuration errors observed during validation.",
    )

    # Whether the worker should invest more turns in this path.
    retryable: bool = Field(
        default=False,
        description="True when the worker should consider retrying or extending this workflow.",
    )

    # Short explanation of why the workflow received its status.
    confidence_notes: str = Field(
        default="",
        description="Concise rationale for the validation status.",
    )


class TestingReport(BaseModel):
    """Typed handoff from the workflow tester to the execution worker."""

    # Overall route for the next stage. "ready" means at least one
    # workflow validated cleanly; "partial" means some path is promising
    # but not fully de-risked; "blocked" means nothing runnable was found.
    overall_status: Literal["ready", "partial", "blocked"] = Field(
        description="Summary status across all validated workflows."
    )

    # One record per tested workflow. This is the authoritative source;
    # aggregate name lists below are convenience summaries.
    workflows: list[WorkflowValidation] = Field(
        default_factory=list,
        description="Per-workflow validation results.",
    )

    # Aggregate name lists are useful in prompts and saved JSON because a
    # quick scan shows what is runnable without re-reading each record.
    validated_workflows: list[str] = Field(
        default_factory=list,
        description="Names of workflows whose smoke tests passed cleanly.",
    )
    partial_workflows: list[str] = Field(
        default_factory=list,
        description="Names of workflows that partially validated.",
    )
    blocked_workflows: list[str] = Field(
        default_factory=list,
        description="Names of workflows blocked by missing inputs or external constraints.",
    )
    failed_workflows: list[str] = Field(
        default_factory=list,
        description="Names of workflows that ran but failed due to runtime/config issues.",
    )

    # Top-level summaries help the worker and humans scan the handoff.
    recommendations: list[str] = Field(
        default_factory=list,
        description="Concrete suggestions for the downstream worker.",
    )
    notes: str = Field(
        default="",
        description="Additional context for the downstream worker.",
    )


def canonicalize_testing_report(report: TestingReport) -> TestingReport:
    """Recompute aggregate fields from ``report.workflows``.

    The workflow records are the source of truth. Recomputing the summary
    fields here prevents prompt drift or a partially-filled model output
    from handing the worker contradictory lists such as a workflow marked
    "validated" but also listed under "failed_workflows".
    """

    validated: list[str] = []
    partial: list[str] = []
    blocked: list[str] = []
    failed: list[str] = []

    for workflow in report.workflows:
        if workflow.status == "validated":
            validated.append(workflow.workflow_name)
        elif workflow.status == "partial":
            partial.append(workflow.workflow_name)
        elif workflow.status == "blocked":
            blocked.append(workflow.workflow_name)
        else:
            failed.append(workflow.workflow_name)

    if validated:
        overall: Literal["ready", "partial", "blocked"] = "ready"
    elif partial:
        overall = "partial"
    else:
        overall = "blocked"

    return report.model_copy(
        update={
            "overall_status": overall,
            "validated_workflows": validated,
            "partial_workflows": partial,
            "blocked_workflows": blocked,
            "failed_workflows": failed,
        }
    )


def format_testing_report_for_worker(report: TestingReport) -> str:
    """Render a ``TestingReport`` as a prompt preamble for the worker.

    Kept as a pure string builder so team orchestration can inject a
    deterministic summary without asking the LLM to paraphrase its own
    prior output. This also gives unit tests a stable seam.
    """

    report = canonicalize_testing_report(report)
    lines = [
        "WORKFLOW TESTING REPORT (from the validation stage - reuse this evidence):",
        f"- overall_status: {report.overall_status}",
    ]
    if report.validated_workflows:
        lines.append(f"- validated: {', '.join(report.validated_workflows)}")
    if report.partial_workflows:
        lines.append(f"- partial: {', '.join(report.partial_workflows)}")
    if report.blocked_workflows:
        lines.append(f"- blocked: {', '.join(report.blocked_workflows)}")
    if report.failed_workflows:
        lines.append(f"- failed: {', '.join(report.failed_workflows)}")
    if report.recommendations:
        lines.append("- recommendations: " + " | ".join(report.recommendations))
    if report.notes:
        lines.append(f"- notes: {report.notes}")

    if report.workflows:
        lines.append("\nPer-workflow evidence:")
    for workflow in report.workflows:
        detail = [f"* {workflow.workflow_name} [{workflow.status}]"]
        if workflow.paper_reference:
            detail.append(f"paper={workflow.paper_reference}")
        if workflow.files_staged:
            detail.append(f"staged={', '.join(workflow.files_staged)}")
        if workflow.commands_run:
            detail.append(f"commands={'; '.join(workflow.commands_run)}")
        if workflow.observed_outputs:
            detail.append(f"observed={'; '.join(workflow.observed_outputs)}")
        if workflow.missing_inputs:
            detail.append(f"missing={'; '.join(workflow.missing_inputs)}")
        if workflow.dependency_issues:
            detail.append(f"deps={'; '.join(workflow.dependency_issues)}")
        if workflow.runtime_errors:
            detail.append(f"errors={'; '.join(workflow.runtime_errors)}")
        if workflow.confidence_notes:
            detail.append(f"notes={workflow.confidence_notes}")
        lines.append(" | ".join(detail))

    lines.append(
        "\nUse the validated workflows first. Do not re-discover the repo from scratch unless "
        "the testing report is clearly insufficient or contradictory."
    )
    return "\n".join(lines)


TESTING_INSTRUCTIONS = """\
You are the WORKFLOW TESTING AGENT. Your job is to validate candidate
paper/repository workflows BEFORE the main reasoning worker spends a large
turn budget on them.

If the input contains explicit workflow definitions, validate those. If not,
derive a SMALL set of candidate workflows from the question and repo.

WORKFLOW
--------
1. ORIENT - Read the question and paper briefly. Inspect the repo for the
   scripts/configs/inputs relevant to the candidate workflows.

2. VERIFY INPUTS - Check whether the required paths, configs, weights, and
   example data can actually be resolved. Use resolve_repo_path(),
   find_repo_files(), list_paper_artifacts(), and read_repo_file().

3. STAGE + SMOKE TEST - Stage only the files needed for validation into the
   workspace. Run lightweight checks such as:
   - `python -c "import ..."` smoke imports
   - `python script.py --help`
   - a minimal example invocation
   - reading the output artifact location after the command
   Use execute_command() for real checks, not just static inspection.

4. CLASSIFY - For each workflow, decide:
   - validated - the workflow starts/runs and produces expected output shape/location
   - partial - promising, but incomplete/risky (e.g. imports work, CLI starts, artifact not fully produced)
   - blocked - missing input, weight, gated resource, or incompatible hardware/environment
   - failed - command ran but hit a real runtime/configuration error

5. HAND OFF - Produce a TestingReport the downstream worker can trust.
   Prefer concrete, short evidence over long prose. Recommendations should
   tell the worker what to try first and what to avoid.

RULES
-----
- This stage validates workflows; it does NOT answer the benchmark question.
- Perform real validation checks. Static guesses are not enough.
- Keep checks lightweight: prefer smoke tests and minimal runs over full experiments.
- When a workflow is blocked, say exactly what is missing or incompatible.
- Only mark a workflow validated if you observed real evidence from command
  output or generated artifacts in this run.
"""


_TESTING_TOOLS = [
    read_paper,
    list_repo_files,
    find_repo_files,
    resolve_repo_path,
    search_repo,
    read_repo_file,
    write_file,
    stage_repo_path,
    execute_command,
    list_workspace_files,
    read_workspace_file,
    list_paper_artifacts,
    stage_paper_artifact,
    venv_status,
]


def create_testing_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the workflow-testing agent."""
    return Agent(
        name="Workflow Testing Agent",
        instructions=TESTING_INSTRUCTIONS,
        tools=_TESTING_TOOLS,
        model=model,
        output_type=TestingReport,
    )


def create_execution_agent_with_testing(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the execution worker used after a testing-stage handoff.

    The worker prompt stays close to ``REACT_INSTRUCTIONS_IMPROVED`` so
    the comparison against existing teams remains meaningful; the testing
    report is injected as ordinary input text by the team orchestration.
    """
    return Agent(
        name="ReAct Execution Worker (testing-aware)",
        instructions=REACT_INSTRUCTIONS_IMPROVED,
        tools=_TESTING_TOOLS,
        model=model,
        output_type=ReActAnswer,
    )
