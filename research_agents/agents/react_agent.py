# ReAct agent for Paper2AgentBench evaluation.
#
# Forces the agent to produce explicit Thought / Action / Observation /
# Reflection steps for every tool call, then collects the full chain into
# the structured output alongside a final answer to the benchmark question.
#
# Usage:
#   uv run python -m research_agents.react_main \
#     --project papers/<slug> \
#     --question "..." \
#     --ground-truth "..." \
#     --id REPO_001 \
#     --biorxiv-url "https://biorxiv.org/..."

from typing import Literal

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
from research_agents.tools.exec_tools import (
    cache_workspace_artifact,
    write_file,
    stage_repo_path,
    execute_command,
    list_workspace_files,
    list_paper_artifacts,
    read_workspace_file,
    stage_paper_artifact,
    venv_status,
)


# --- Structured output models ---


class ReActStep(BaseModel):
    """One Thought → Action → Observation → Reflection cycle."""

    step: int = Field(description="Step number, starting from 1")
    thought: str = Field(
        description="What you intend to do in this step and why, written BEFORE calling the tool"
    )
    action: str = Field(
        description="The exact tool call or command you executed, "
        "e.g. 'read_paper()' or 'execute_command(\"python predict.py\")'"
    )
    observation: str = Field(
        description="Concise summary of what the tool returned (truncate long outputs)"
    )
    reflection: str = Field(
        description="What you conclude from this observation and how it shapes the next step"
    )


class ReActAnswer(BaseModel):
    """Top-level output for a single Paper2AgentBench question."""

    chain: list[ReActStep] = Field(
        description="All T/A/O/R steps taken to reach the final answer. "
        "Every tool call must appear as its own step."
    )
    final_answer: str = Field(
        description="Direct, concise answer to the benchmark question. "
        "For yes/no questions use 'Yes' or 'No'. "
        "For numeric questions include the value and units. "
        "For name/method questions give the exact name from the paper."
    )
    # Set to "blocked" when the benchmark question could not be answered
    # from the available repo, environment, or generated outputs.
    answer_status: Literal["answered", "blocked"] = Field(
        default="answered",
        description="Whether the question was answered or blocked by an external/local issue.",
    )
    # Machine-readable category for blocked answers; "none" is used for
    # successful answers so downstream summaries do not need to infer it
    # from free-form text.
    blocker_type: Literal[
        "none",
        "missing_input",
        "missing_weights",
        "missing_dependency",
        "external_download",
        "gpu_required",
        "runtime_error",
        "ambiguous_question",
        "unknown",
    ] = Field(
        default="none",
        description="Primary blocker category when answer_status is blocked.",
    )
    # Human-readable explanation of why the answer is blocked.  This is
    # intentionally separate from final_answer, which stays concise for
    # benchmark scoring.
    blocker_explanation: str | None = Field(
        default=None,
        description="Clear explanation of why the worker could not answer.",
    )
    # Short evidence snippets from real observations, such as exact missing
    # paths, checkpoint names, timeout messages, or import errors.
    blocker_evidence: list[str] = Field(
        default_factory=list,
        description="Observed evidence supporting the blocker classification.",
    )


# --- System prompt ---


REACT_INSTRUCTIONS = """\
You are an expert research assistant that reads scientific papers and their
code repositories to answer benchmark questions.

You MUST answer the question by working through a series of explicit
Thought / Action / Observation / Reflection (T/A/O/R) steps.

CRITICAL RULES FOR THE CHAIN
─────────────────────────────
1. Record EVERY tool call as its own step — do not batch multiple calls
   into one step.
2. For each step, fill in all four fields in order:
   • thought     — what you intend to do and WHY, written BEFORE the call
   • action      — the exact tool call, e.g. read_paper() or
                   execute_command("python run.py --flag")
   • observation — concise summary of what the tool returned
   • reflection  — what you conclude and what you will do next
3. Number steps sequentially starting at 1.
4. Aim for at least 3 steps; complex questions typically need 5–15.

WORKFLOW
────────
1. UNDERSTAND  — Call read_paper() first. Identify what the question is
                 asking. Decide whether execution is required.

2. EXPLORE     — Map the repo completely before touching workspace/.

     STEP 1 — Full tree scan (mandatory, always first):
     Call list_repo_files(). This returns readable text files in the repo
     recursively. Then call find_repo_files() for artifact suffixes relevant
     to the question (.pth, .pt, .pkl, .npy, .npz, .fasta, .fa, .tsv, .csv,
     .xlsx). Read both listings carefully. Do not skip binary artifacts.

     STEP 2 — Locate the files the question asks for:
     For every path copied from the question, first call resolve_repo_path()
     with the original path string.
     • If resolve_repo_path returns an exact or prefix-stripped match → use it.
     • If it returns candidates → inspect the most relevant candidate(s).
     • If it returns no candidates → do NOT give up. Execute the full search
       protocol below before concluding anything is missing.

     SEARCH PROTOCOL (exhaust ALL steps before reporting not found):
     a. Extract just the filename (e.g. "receptor.fasta" from
        "PPLM/notebooks/run_pplm/data/receptor.fasta") and call
        find_repo_files("receptor.fasta"). The repo may have been reorganised
        since the question was written.
     b. If step (a) finds nothing, try a distinctive stem or extension:
        search_repo("receptor"), search_repo(".fasta"). Cast wide.
     c. Look at the directory structure in the full listing to find the
        closest matching subfolder and call read_repo_file() on a config
        or README there to understand the actual layout.
     d. Try likely renamed variants the question author may have used
        (e.g. "seq1.fasta" → search "seq1", "seq_1", "sequence1").
     e. If a parent directory from the question path exists under a
        different root, check it: find_repo_files() and search_repo() with
        the parent folder name.

     For pretrained weights or generated artifacts, use find_repo_files(),
     not search_repo(). Content grep cannot see large/binary files like
     .pth, .pt, .pkl, .npy, .npz, or .xlsx.

     Only after all five steps return nothing should you conclude the file
     is genuinely absent. At that point set final_answer to:
     "Required file '<original path from question>' not found in repo after
     exhaustive search — cannot proceed."

     NEVER stage or execute a path that did not appear in an actual
     list_repo_files(), find_repo_files(), resolve_repo_path(), or
     search_repo() result.


3. EXECUTE     — If the question requires running code:
   • stage_repo_path() to copy scripts/data into workspace/
   • Before downloading weights or regenerating expensive outputs, call
     list_paper_artifacts(). If a reusable artifact is already cached, call
     stage_paper_artifact() instead of downloading/regenerating it.
   • Before installing dependencies, call venv_status() to see what is
     already available in the shared per-paper venv.
   • execute_command() to install dependencies and run experiments
   • If you download a model weight, produce a pickle/NumPy array, or create
     any output that another question for this paper could reuse, call
     cache_workspace_artifact() after verifying it exists.
   • If a Python import fails with `ModuleNotFoundError`, run
     `pip install <package>` with `timeout=3600` before rewriting
     the script or giving up.
   • read_workspace_file() to inspect output files
   • Retry failures up to 5 times per experiment; record each attempt.

4. ANSWER      — Set final_answer to a direct, concise answer:
   • Yes / No for boolean questions
   • The exact numeric value (with units) for numeric questions
   • The exact method or model name for identification questions
   • A short phrase for other questions
   • Set answer_status="answered" and blocker_type="none" when you answered.

   If you cannot answer, set:
   • answer_status="blocked"
   • blocker_type to exactly one of:
     missing_input, missing_weights, missing_dependency, external_download,
     gpu_required, runtime_error, ambiguous_question, unknown
   • blocker_explanation to 1-3 sentences explaining the real blocker.
   • blocker_evidence to short direct evidence from tool output, such as the
     missing path, missing checkpoint filename, timeout, or import error.


  INTEGRITY RULES
  ───────────────
  - Base every observation and final_answer on what you actually read or ran.
  - Never copy paper-reported numbers into key findings as if you produced them.
  - If a question says run, process, merge, predict, or generate, README
    examples are not sufficient evidence. You must execute or read a
    generated artifact in the current chain, otherwise say EXECUTION_REQUIRED.
  - For ESM/ESM-2 embeddings, raw token embeddings often include BOS/EOS
    special tokens. When the question asks for per-residue rows or sequence
    length, strip special tokens or use the original residue count.
  - Do not fabricate tool outputs or results.

  MANDATORY FINAL ANSWER FORMAT ON FAILURE:
  - If you did not successfully execute code AND read its actual printed output
    or generated artifact in the current chain, your final_answer MUST be exactly:
    "EXECUTION_REQUIRED — <one sentence reason why execution failed>"
    Also set answer_status="blocked", blocker_type, blocker_explanation,
    and blocker_evidence.
  - Never set final_answer to a specific numeric value unless you personally
    read that value from real tool output in the current chain.
  - "I think the answer might be X" is not allowed. Either you ran it and
    observed X, or you say EXECUTION_REQUIRED.
"""


def create_react_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the ReAct research agent (baseline prompt)."""
    return Agent(
        name="ReAct Research Assistant",
        instructions=REACT_INSTRUCTIONS,
        tools=[
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
            cache_workspace_artifact,
            venv_status,
        ],
        model=model,
        output_type=ReActAnswer,
    )


# Improved-variant prompt: same skeleton as REACT_INSTRUCTIONS plus two
# targeted bullets the baseline lacks.  Kept here so the diff against the
# baseline is one search-and-replace per bullet rather than an entire
# duplicate prompt — anyone curious about what "improved" really means
# can compare these inserts directly against the baseline.
_ESM_STRIP_BULLET = """\
   • If a Python import fails with `ModuleNotFoundError`, run
     `pip install <package>` with `timeout=3600` before rewriting
     the script or giving up.
   • For ESM-2 / fair-esm embeddings: the per-token tensor returned by the
     model has shape `(L+2, D)` where `L` is the input sequence length;
     positions `0` and `L+1` are the BOS and EOS special tokens. When the
     question asks for a per-residue row, the residue count, or anything
     that should match the FASTA length, slice with `embeddings[1:-1]`
     before computing the answer. Sanity-check the stripped row count
     against the FASTA's residue count before reporting."""

_SYNTHESIS_CARVEOUT = """\
  - For ESM/ESM-2 embeddings, raw token embeddings often include BOS/EOS
    special tokens. When the question asks for per-residue rows or sequence
    length, strip special tokens or use the original residue count.
  - Tool-deterministic synthesis carve-out: if a question describes a tool
    whose output is fully determined by ANY valid input that exercises the
    requested behavior (e.g. a padding tool whose output length depends only
    on the target length, or a generator that produces a fixed number of
    sequences regardless of seed content), and the literal input file
    referenced in the question text is missing from the repo after the
    exhaustive search protocol, you MAY synthesize a minimal valid input
    that exercises the requested behavior. Stage the synthesized file at
    the workspace path the question requests, run the tool, and report the
    output it produced. Record the synthesis in your reflection. This
    carve-out does NOT apply to ML inference, statistics, benchmarks, or
    any output whose value depends on the specific content of the input."""


def _build_improved_instructions() -> str:
    """Return REACT_INSTRUCTIONS with the two improved-variant bullets spliced in.

    Computed at import time so the constant below is just a string the rest
    of the code can read like REACT_INSTRUCTIONS.  Asserts the splice points
    actually exist — a future refactor of REACT_INSTRUCTIONS that drops one
    of the anchor lines will fail loudly here instead of silently producing
    a prompt identical to the baseline.
    """
    text = REACT_INSTRUCTIONS
    esm_anchor = (
        "   • If a Python import fails with `ModuleNotFoundError`, run\n"
        "     `pip install <package>` with `timeout=3600` before rewriting\n"
        "     the script or giving up."
    )
    integrity_anchor = (
        "  - For ESM/ESM-2 embeddings, raw token embeddings often include BOS/EOS\n"
        "    special tokens. When the question asks for per-residue rows or sequence\n"
        "    length, strip special tokens or use the original residue count."
    )
    if esm_anchor not in text:
        raise RuntimeError(
            "REACT_INSTRUCTIONS no longer contains the ESM-strip anchor; "
            "update _ESM_STRIP_BULLET in react_agent.py."
        )
    if integrity_anchor not in text:
        raise RuntimeError(
            "REACT_INSTRUCTIONS no longer contains the integrity-rules anchor; "
            "update _SYNTHESIS_CARVEOUT in react_agent.py."
        )
    text = text.replace(esm_anchor, _ESM_STRIP_BULLET, 1)
    text = text.replace(integrity_anchor, _SYNTHESIS_CARVEOUT, 1)
    return text


REACT_INSTRUCTIONS_IMPROVED = _build_improved_instructions()


def create_react_agent_improved(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the ReAct research agent with the improved-variant prompt.

    Identical tool registration to ``create_react_agent``; the only
    difference is the system prompt, which adds:
      * an explicit ESM-2 BOS/EOS stripping rule under EXECUTE, and
      * a tool-deterministic synthesis carve-out under INTEGRITY RULES.

    Used by the ``worker-critic-plus`` team.  Pair with
    ``resolve_project(apply_setup=True)`` so up-front weight downloads
    (e.g. PPLM's ``weights/download.sh``) also run.
    """
    return Agent(
        name="ReAct Research Assistant (improved)",
        instructions=REACT_INSTRUCTIONS_IMPROVED,
        tools=[
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
            cache_workspace_artifact,
            venv_status,
        ],
        model=model,
        output_type=ReActAnswer,
    )
