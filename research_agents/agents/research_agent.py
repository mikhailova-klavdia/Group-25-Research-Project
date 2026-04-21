# Agent definition for the research assistant.
#
# The agent gets nine tools: four for reading (paper + repo), and five
# for staging, writing, executing, and inspecting results in the
# workspace.  It returns structured output via ResearchAnswer which
# can contain zero or more ExperimentResult entries.

from pydantic import BaseModel, Field

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.paper_tools import read_paper
from research_agents.tools.repo_tools import list_repo_files, read_repo_file, search_repo
from research_agents.tools.exec_tools import (
    write_file,
    stage_repo_path,
    execute_command,
    list_workspace_files,
    read_workspace_file,
)


# --- Structured output models ---


class ExperimentResult(BaseModel):
    """Captures one experiment the agent attempted to reproduce.

    One ExperimentResult is produced per experiment ATTEMPTED, regardless
    of whether execution succeeded.  Failed attempts are data too: they
    tell the reader which paper claims could not be verified in this
    environment (and why).
    """

    # Human-readable label for the experiment; shown verbatim in the CLI
    # output and used by downstream tooling to cross-reference runs.
    name: str = Field(description="Short name, e.g. 'PPI prediction on example pair'")

    # Traceability: points the reader to the section/table/figure of the
    # paper this experiment corresponds to.  Helps the user verify that
    # the agent is not hallucinating experiments that don't exist.
    paper_reference: str = Field(
        description="Where this experiment is described in the paper, "
        "e.g. 'Section 4.2, Table 1'"
    )

    # Scripts actually invoked — either from the staged repo contents or
    # helpers the agent wrote into the workspace.
    scripts_used: list[str] = Field(
        description="Scripts executed (repo scripts or agent-created)"
    )

    # Full shell commands run for this experiment, so the user can
    # reproduce the exact invocation outside the agent if they want to.
    commands_run: list[str] = Field(
        description="All shell commands executed for this experiment"
    )

    # True only if the experiment produced usable results.  A setup step
    # that installs a dependency is NOT an experiment; success=False
    # means the paper's claim could not be verified.
    success: bool

    # Results the agent *produced itself* — metrics, counts, logs.  The
    # prompt explicitly forbids copying paper-reported numbers in here.
    key_findings: list[str] = Field(
        description="Quantitative or qualitative results, "
        "e.g. ['Accuracy: 0.95', 'AUC: 0.87']"
    )

    # Paths (relative to workspace/) of files the experiment produced.
    # Default is an empty list because some experiments only print to
    # stdout; marking this field optional keeps the structured output
    # from getting noisy on read-only or trivial cases.
    output_files: list[str] = Field(
        default_factory=list,
        description="Files produced in the workspace",
    )

    # What the findings mean relative to the paper's claim.  Required,
    # because raw numbers without interpretation are close to useless.
    interpretation: str = Field(
        description="What the results mean in the context of the paper"
    )

    # Optional because some experiments have nothing paper-reported to
    # compare against (e.g. the paper only gives qualitative claims).
    paper_comparison: str | None = Field(
        default=None,
        description="How the reproduced results compare with the paper's reported results",
    )

    # Populated only when success=False; describes the blocker (missing
    # weights, timeout, license gate, etc.) in enough detail that the
    # user can decide whether to unblock and retry.
    error_summary: str | None = None

    # Total execution attempts the agent made for this experiment before
    # recording this result.  Defaults to 1 meaning "succeeded or gave up
    # on first try"; if the agent retried failures (the prompt allows up
    # to 5 retries per experiment), the agent should set this field to
    # the final count so the user can tell at a glance whether the run
    # converged quickly or only after heavy iteration.
    attempts: int = 1


class ResearchAnswer(BaseModel):
    """Top-level structured output returned by the agent."""

    answer: str = Field(description="Executive summary of everything the agent did and found")
    reasoning: str = Field(
        description="Detailed reasoning referencing paper sections and repo files"
    )
    sources: list[str] = Field(description="Paper path and relevant repo/workspace file paths")
    experiments: list[ExperimentResult] = Field(
        default_factory=list,
        description="Per-experiment results. Empty for read-only questions.",
    )
    overall_interpretation: str | None = Field(
        default=None,
        description="Cross-experiment synthesis when multiple experiments were run",
    )
    reproducibility_assessment: str | None = Field(
        default=None,
        description="Overall judgement on how well the paper's results were reproduced "
        "and any discrepancies observed",
    )


# --- System prompt ---

INSTRUCTIONS = """\
You are an expert research assistant that can read scientific papers, explore
codebases, and reproduce experiments from a fresh local run workspace.

Your goal is to understand the paper, identify the experiments it describes,
execute as many of them as possible using the provided repository, interpret
the results, and assess reproducibility.

Your workflow has six phases:

1. UNDERSTAND
   - Read the user's question carefully.
   - Use read_paper to read the project paper thoroughly.
   - Use list_repo_files, search_repo, and read_repo_file to explore the
     repository.  Understand the methodology, available data, dependencies,
     and how scripts are meant to be run.
   - If the user asks a read-only question (no execution required), skip to
     phase 6 and answer directly.

2. PLAN
   - Identify ALL experiments described in the paper: tables with metrics,
     figures with numerical results, ablation studies, baseline comparisons,
     case studies.  List them.
   - Map each experiment to the repo scripts, data, and config files that
     implement it.
   - Determine which experiments are feasible to run in this environment
     (consider: model weights available? data too large? GPU required?
     external databases needed?).  Mark infeasible ones and explain why.
   - Order the feasible experiments by dependency: shared setup first
     (e.g. install deps, download weights), then experiments that build on
     each other.
   - Plan the exact commands for every experiment.

3. SETUP
   - Install dependencies once at the start.  Use "pip install ..." or
     "uv pip install ..." — they go into the isolated run venv only.
   - Use stage_repo_path to copy scripts, modules, configs, and data into
     the workspace.  Stage liberally — it is cheap.
   - Use write_file to create helper scripts, wrappers, or modified configs
     when needed.
   - The shared repo is input-only.  Never execute in or write to repo/.
   - execute_command always runs from the workspace.
   - Environment variables available inside commands:
     RESEARCH_PROJECT_PATH, RESEARCH_REPO_PATH, RESEARCH_PAPER_PATH,
     RESEARCH_RUN_PATH, RESEARCH_WORKSPACE_PATH.
   - The shared repo root is already on PYTHONPATH.

4. EXECUTE
   - Run each experiment from the plan, one at a time.
   - After each command, check the output.  If a script produces output
     files (CSVs, logs, JSON, text), use read_workspace_file to inspect
     them.
   - If an experiment fails, read the error carefully, adjust your
     approach, and retry.  You may retry each experiment up to 5 times.
   - After 5 failed attempts on one experiment, record the failure and
     move on to the next experiment.
   - Do NOT stop at the first failure — attempt every feasible experiment.
   - When a component is blocked (license gate, missing weights, API
     token required, gated dataset), keep running whatever is not
     blocked.  A run that blocks on a gated model but still produces
     sklearn baselines is far more useful than one that abandons
     everything.
   - When an error message lists workarounds (public checkpoint, non-
     gated model version, alternative example script, env var to set),
     try those before reporting the problem to the user.  "Tell the
     user to do X manually" is a last resort, not a first response.

5. INTERPRET
   - For each experiment that succeeded, read and analyse the output files
     and stdout using read_workspace_file and execute_command.
   - Extract key quantitative results (metrics, scores, counts).
   - Compare each result against the corresponding value reported in the
     paper.  Note agreements, discrepancies, and possible explanations
     (different hardware, stochastic variance, subset of data, etc.).
   - If multiple experiments were run, synthesise the findings: do the
     results collectively support or challenge the paper's claims?

6. REPORT
   - Provide a clear executive summary in the answer field.
   - Fill in the reasoning with detailed, evidence-based analysis
     referencing specific paper sections and repo files.
   - List all relevant file paths in sources.
   - Fill in one ExperimentResult per experiment (both successes and
     failures).
   - If experiments were run, fill in overall_interpretation with a
     cross-experiment synthesis.
   - Fill in reproducibility_assessment with your overall judgement on
     how well the results were reproduced.
   - If the question was read-only, leave experiments empty and omit the
     optional fields.

Guidelines:
- Base everything on the paper and repository content.  Do not fabricate.
- Paper-reported numbers are NOT your results.  If you could not run a
  given experiment, record a failed ExperimentResult — never copy the
  paper's claimed metrics into key_findings or interpretation as if you
  had produced them yourself.
- Every experiment attempt gets an ExperimentResult, success or failure.
  Failed attempts are data: they show the user what was blocked and why.
- Prefer existing repo scripts — do not reinvent what already exists.
- repo/ is input-only.  Stage what you need into workspace/.
- All new scripts and outputs go in workspace/.
- Use list_repo_files first when you need orientation.
- Use read_workspace_file to inspect output files — do not guess results.
- Never use system python or pip directly — they are already routed to
  the project venv.  Just call "python" or "pip install" normally.
- Be thorough but realistic.  It is better to run 3 experiments well than
  to rush through 10 with superficial analysis.
"""


def create_research_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build a research agent wired up with reading and execution tools."""
    return Agent(
        name="Research Assistant",
        instructions=INSTRUCTIONS,
        tools=[
            read_paper,
            list_repo_files, search_repo, read_repo_file,
            write_file, stage_repo_path, execute_command,
            list_workspace_files, read_workspace_file,
        ],
        model=model,
        output_type=ResearchAnswer,
    )
