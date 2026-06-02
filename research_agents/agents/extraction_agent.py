"""Extraction agent for paper-to-workflow and repo-to-tool analysis.

This stage sits before workflow testing and execution.  It reads the
paper plus repository structure, identifies candidate experimental
workflows, and emits a structured inventory that downstream agents can
reuse instead of rediscovering the same scripts and inputs repeatedly.
"""

from pydantic import BaseModel, Field

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.paper_tools import read_paper
from research_agents.tools.repo_tools import (
    find_repo_files,
    list_repo_files,
    read_repo_file,
    resolve_repo_path,
    search_repo,
)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    """Return ``items`` without duplicates while preserving first-seen order.

    The extraction stage aggregates paths and labels from several workflow
    records.  Stable order keeps the saved JSON readable and makes tests
    deterministic, while deduplication avoids noisy top-level summaries.
    """

    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


class WorkflowDefinition(BaseModel):
    """Structured description of one experiment or runnable workflow.

    Each entry captures the paper claim plus the concrete repo assets
    that appear to implement it.  Downstream agents use this record as a
    starting point for validation and execution rather than re-scanning
    the repository from scratch.
    """

    # Short stable name so later stages can refer to a workflow without
    # having to quote a long paragraph from the paper.
    workflow_name: str = Field(description="Short label for the workflow or experiment.")

    # Traceability back to the paper when the mapping is known; blank
    # references are allowed when the repo suggests a workflow the paper
    # text does not locate precisely.
    paper_reference: str | None = Field(
        default=None,
        description="Section, figure, or table this workflow corresponds to, if known.",
    )

    # Distinguishes confident mappings from partial or speculative ones so
    # later stages know where human judgement is still required.
    confidence: str = Field(
        default="medium",
        description="Confidence label such as high, medium, or low.",
    )

    # Human-readable explanation of the workflow's purpose.  This gives
    # later agents the intent behind the scripts, not just filenames.
    objective: str = Field(
        default="",
        description="What this workflow appears to do and why it exists.",
    )

    # Repo scripts or notebooks that appear to implement this workflow.
    repo_entrypoints: list[str] = Field(
        default_factory=list,
        description="Scripts, notebooks, or modules likely used to run this workflow.",
    )

    # Configs are separated from entrypoints because later stages often
    # need to inspect or tweak them independently of the main script.
    config_files: list[str] = Field(
        default_factory=list,
        description="Config files associated with the workflow.",
    )

    # Inputs are first-class because workflow testing needs to know which
    # paths or artifacts must exist before any command can succeed.
    required_inputs: list[str] = Field(
        default_factory=list,
        description="Data files, checkpoints, or other inputs the workflow expects.",
    )

    # The question benchmark often asks for generated values or files; this
    # field gives downstream agents a target to look for.
    expected_outputs: list[str] = Field(
        default_factory=list,
        description="Artifacts, metrics, or files the workflow should produce.",
    )

    # Dependency hints are extracted separately from concrete input files
    # because missing packages and missing checkpoints are handled differently.
    dependency_hints: list[str] = Field(
        default_factory=list,
        description="Packages, frameworks, or hardware assumptions suggested by the repo.",
    )

    # Allows the extractor to make explicit where multiple scripts or
    # paper sections could plausibly map to the same workflow.
    ambiguity_notes: list[str] = Field(
        default_factory=list,
        description="Uncertainties or alternative mappings for this workflow.",
    )

    # General catch-all for small but useful details that do not belong in
    # the other structured fields, such as CLI flag names or README caveats.
    notes: str = Field(
        default="",
        description="Additional concise notes about the workflow mapping.",
    )


class PaperRepoLink(BaseModel):
    """One mapping from a paper claim to repository assets."""

    paper_reference: str = Field(description="Section, figure, or table in the paper.")
    repo_assets: list[str] = Field(
        default_factory=list,
        description="Repo files or modules that appear related to that paper reference.",
    )
    rationale: str = Field(
        default="",
        description="Why these repo assets appear to match the paper reference.",
    )


class ExtractionReport(BaseModel):
    """Typed handoff from extraction to testing and execution stages."""

    # Short paper-level summary so downstream stages can orient without
    # paying the cost of re-reading the entire paper every time.
    paper_summary: str = Field(description="Concise summary of the paper.")

    # Makes the central task explicit; useful when the repo contains
    # several utilities but only one main scientific objective.
    research_objective: str = Field(description="The paper's core research objective.")

    # Human-readable list of major experiments or evaluations inferred
    # from the paper/repo pair.  This is a quick scan field; the detailed
    # implementation mapping lives in workflow_definitions below.
    identified_experiments: list[str] = Field(
        default_factory=list,
        description="Major experiments or evaluation tracks identified by extraction.",
    )

    # One record per candidate workflow, including scripts, configs, and
    # expected inputs/outputs for downstream validation.
    workflow_definitions: list[WorkflowDefinition] = Field(
        default_factory=list,
        description="Structured workflow inventory extracted from paper and repo.",
    )

    # Aggregate path lists are derived from the workflow entries so later
    # stages can scan likely files quickly without traversing every record.
    repo_entrypoints: list[str] = Field(
        default_factory=list,
        description="All unique repo entrypoints aggregated from the workflows.",
    )
    config_files: list[str] = Field(
        default_factory=list,
        description="All unique config files aggregated from the workflows.",
    )
    input_artifacts: list[str] = Field(
        default_factory=list,
        description="All unique required inputs aggregated from the workflows.",
    )
    expected_outputs: list[str] = Field(
        default_factory=list,
        description="All unique expected outputs aggregated from the workflows.",
    )

    # Explicit paper-to-repo mappings make it easier to audit whether the
    # extractor grounded an experiment in actual repo assets.
    paper_repo_links: list[PaperRepoLink] = Field(
        default_factory=list,
        description="Mappings from paper references to repo assets.",
    )

    # Ambiguities and gaps are surfaced at the top level so later stages
    # can treat them as known uncertainty instead of silent omission.
    ambiguous_mappings: list[str] = Field(
        default_factory=list,
        description="Mappings that remain uncertain or under-specified.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Inputs, configs, or details that could not be found during extraction.",
    )
    notes: str = Field(
        default="",
        description="Additional concise extraction notes for downstream agents.",
    )


def canonicalize_extraction_report(report: ExtractionReport) -> ExtractionReport:
    """Recompute aggregate fields from the workflow and link records.

    The workflow list is the source of truth.  Rebuilding the aggregate
    entrypoint/config/input/output lists keeps the report internally
    consistent even if the model fills those summary fields incompletely.
    """

    repo_entrypoints: list[str] = []
    config_files: list[str] = []
    input_artifacts: list[str] = []
    expected_outputs: list[str] = []
    identified_experiments = list(report.identified_experiments)
    ambiguous_mappings = list(report.ambiguous_mappings)

    for workflow in report.workflow_definitions:
        identified_experiments.append(workflow.workflow_name)
        repo_entrypoints.extend(workflow.repo_entrypoints)
        config_files.extend(workflow.config_files)
        input_artifacts.extend(workflow.required_inputs)
        expected_outputs.extend(workflow.expected_outputs)
        ambiguous_mappings.extend(workflow.ambiguity_notes)

    for link in report.paper_repo_links:
        repo_entrypoints.extend(link.repo_assets)

    return report.model_copy(
        update={
            "identified_experiments": _dedupe_preserve_order(identified_experiments),
            "repo_entrypoints": _dedupe_preserve_order(repo_entrypoints),
            "config_files": _dedupe_preserve_order(config_files),
            "input_artifacts": _dedupe_preserve_order(input_artifacts),
            "expected_outputs": _dedupe_preserve_order(expected_outputs),
            "ambiguous_mappings": _dedupe_preserve_order(ambiguous_mappings),
        }
    )


def format_extraction_report_for_downstream(report: ExtractionReport) -> str:
    """Render ``report`` as a deterministic prompt preamble.

    The testing and execution stages need a compact structured summary
    they can trust.  Building it in host code avoids asking another LLM
    to paraphrase the extraction output before it can be used.
    """

    report = canonicalize_extraction_report(report)
    lines = [
        "EXTRACTION REPORT (paper/repo understanding stage):",
        f"- research_objective: {report.research_objective}",
        f"- paper_summary: {report.paper_summary}",
    ]
    if report.identified_experiments:
        lines.append("- identified_experiments: " + " | ".join(report.identified_experiments))
    if report.repo_entrypoints:
        lines.append("- repo_entrypoints: " + " | ".join(report.repo_entrypoints))
    if report.config_files:
        lines.append("- config_files: " + " | ".join(report.config_files))
    if report.input_artifacts:
        lines.append("- input_artifacts: " + " | ".join(report.input_artifacts))
    if report.expected_outputs:
        lines.append("- expected_outputs: " + " | ".join(report.expected_outputs))
    if report.ambiguous_mappings:
        lines.append("- ambiguous_mappings: " + " | ".join(report.ambiguous_mappings))
    if report.missing_information:
        lines.append("- missing_information: " + " | ".join(report.missing_information))
    if report.notes:
        lines.append(f"- notes: {report.notes}")

    if report.workflow_definitions:
        lines.append("\nWorkflow inventory:")
    for workflow in report.workflow_definitions:
        detail = [f"* {workflow.workflow_name} [confidence={workflow.confidence}]"]
        if workflow.paper_reference:
            detail.append(f"paper={workflow.paper_reference}")
        if workflow.objective:
            detail.append(f"objective={workflow.objective}")
        if workflow.repo_entrypoints:
            detail.append(f"entrypoints={', '.join(workflow.repo_entrypoints)}")
        if workflow.config_files:
            detail.append(f"configs={', '.join(workflow.config_files)}")
        if workflow.required_inputs:
            detail.append(f"inputs={', '.join(workflow.required_inputs)}")
        if workflow.expected_outputs:
            detail.append(f"outputs={', '.join(workflow.expected_outputs)}")
        if workflow.dependency_hints:
            detail.append(f"deps={', '.join(workflow.dependency_hints)}")
        if workflow.ambiguity_notes:
            detail.append(f"ambiguity={'; '.join(workflow.ambiguity_notes)}")
        if workflow.notes:
            detail.append(f"notes={workflow.notes}")
        lines.append(" | ".join(detail))

    lines.append(
        "\nUse this extraction inventory as the starting map of the paper and repo. "
        "Only rediscover from scratch if the report is clearly insufficient or contradicted by real evidence."
    )
    return "\n".join(lines)


EXTRACTION_INSTRUCTIONS = """\
You are the EXTRACTION AGENT. Your job is to separate paper/repository
understanding from workflow testing and execution.

Read the paper and inspect the repository. Identify the main scientific
workflows, experiments, pipelines, scripts, configs, inputs, and outputs.
Map paper sections/figures/tables to concrete repository assets where
possible. When the mapping is uncertain, surface the ambiguity explicitly.

WORKFLOW
--------
1. Read the paper with read_paper() and summarize the research objective.
2. Explore the repo with list_repo_files(), find_repo_files(), search_repo(),
   resolve_repo_path(), and read_repo_file().
3. Identify the main experiments or runnable workflows described by the
   paper/repo pair.
4. For each workflow, record:
   - the paper reference if known
   - likely repo entrypoints
   - relevant config files
   - required inputs
   - expected outputs
   - dependency hints
   - ambiguity notes where the mapping is not fully clear
5. Produce a structured ExtractionReport rather than free-form prose.

RULES
-----
- Prefer concrete repo assets over vague summaries.
- Do not guess silently. Put uncertainty into ambiguity_notes,
  ambiguous_mappings, or missing_information.
- Include only workflows that are materially grounded in the paper or repo.
- This stage does not execute workflows; it inventories them for downstream agents.
"""


_EXTRACTION_TOOLS = [
    read_paper,
    list_repo_files,
    find_repo_files,
    resolve_repo_path,
    search_repo,
    read_repo_file,
]


def create_extraction_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the paper/repo extraction agent."""
    return Agent(
        name="Extraction Agent",
        instructions=EXTRACTION_INSTRUCTIONS,
        tools=_EXTRACTION_TOOLS,
        model=model,
        output_type=ExtractionReport,
    )
