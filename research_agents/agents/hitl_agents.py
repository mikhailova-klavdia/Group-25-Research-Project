"""Agents for the two-stage ``human-in-the-loop`` team.

Stage 1 is an **Environment Setup Engineer** that prepares the shared
per-paper venv interactively — it discovers dependencies from the repo
itself (there is deliberately no ``.research_config.toml`` to lean on) and
calls ``ask_human`` when it hits something only a person can resolve (a
token, a gated download, a needed workaround). It emits a typed
``EnvReport`` that hands the prepared environment off to Stage 2.

Stage 2 reuses the existing improved ReAct worker prompt
(``REACT_INSTRUCTIONS_IMPROVED``) plus an "ask the human" carve-out and the
``ask_human`` tool, so the executor can request help (e.g. the TabPFN
license-gate → open-V2 workaround) instead of only reporting a blocker.

Both agents reuse the exact tool functions registered on the baseline
worker — nothing in ``react_agent.py`` is modified.
"""

from pydantic import BaseModel, Field

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.hitl import ask_human
from research_agents.project import ResearchContext
from research_agents.agents.react_agent import (
    REACT_INSTRUCTIONS_IMPROVED,
    ReActAnswer,
)
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
    execute_command,
    list_paper_artifacts,
    list_workspace_files,
    read_workspace_file,
    stage_paper_artifact,
    stage_repo_path,
    venv_status,
    write_file,
)


# Both HITL agents share the baseline worker's full tool set plus
# ``ask_human``.  Reusing the same tool objects keeps the setup and
# execution crews capable of the same repo/exec actions; only the prompt
# and ``output_type`` differ between them (the same way ``create_react_agent``
# and ``create_react_agent_improved`` differ only by prompt).
_HITL_TOOLS = [
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
    ask_human,
]


# The triage scout and the read-only answerer only READ (paper + repo) and may
# ask the human — they never install or execute.  This is _HITL_TOOLS minus the
# workspace/execution tools.
_READING_TOOLS = [
    read_paper,
    list_repo_files,
    find_repo_files,
    resolve_repo_path,
    search_repo,
    read_repo_file,
    ask_human,
]


class TriageReport(BaseModel):
    """Routing decision from the Repo Scout: does this question need code execution?

    Produced up front so a read-only question (summarise / explain / "what is this
    repo about") skips the setup and execution stages entirely.  The repo notes are
    reused by whichever path runs, so the exploration is not repeated downstream.
    """

    # The routing gate: True if answering requires running code (installing deps,
    # executing scripts, computing a value); False if it can be answered from the
    # paper + repository text alone.
    needs_execution: bool = Field(
        description="True if answering requires running code; False if it is read-only."
    )
    # One or two sentences on WHY — kept so the saved record explains the route.
    rationale: str = Field(
        default="",
        description="Brief reason for the read-only vs execution decision.",
    )
    # Short description of what the repository is / contains, gathered while
    # deciding the route; reused by the downstream answerer or setup crew.
    repo_overview: str = Field(
        default="",
        description="Short description of what the repo is and contains.",
    )
    # Repo files/dirs found relevant to the question, to seed the next stage.
    relevant_paths: list[str] = Field(
        default_factory=list,
        description="Repo paths relevant to the question (avoids re-discovery downstream).",
    )
    # Any questions the scout asked the human while triaging, for the record.
    human_consults: list[str] = Field(
        default_factory=list,
        description="Questions asked to the human during triage, with answers.",
    )


def format_triage_for_downstream(triage: TriageReport) -> str:
    """Render the Scout's findings as a preamble for the next stage's input."""
    lines = ["REPO SCOUT NOTES (already explored — reuse this, don't re-discover):"]
    if triage.repo_overview:
        lines.append(f"- overview: {triage.repo_overview}")
    if triage.relevant_paths:
        lines.append(f"- relevant paths: {', '.join(triage.relevant_paths)}")
    if triage.rationale:
        lines.append(f"- triage note: {triage.rationale}")
    return "\n".join(lines)


class EnvReport(BaseModel):
    """Typed handover from the setup crew to the execution crew.

    Summarises the state of the per-paper venv after interactive setup, so
    the execution worker starts from a known baseline instead of
    re-discovering the environment from scratch.
    """

    # Whether the environment is ready enough to attempt the question at
    # all.  False signals the execution crew (and the human) that setup
    # could not finish — the gaps explain why.
    venv_ready: bool = Field(
        description="True if the venv is prepared well enough to attempt the question."
    )
    # Best-effort list of packages installed during setup; informational
    # so the worker does not redundantly reinstall them.
    installed_packages: list[str] = Field(
        default_factory=list,
        description="Packages installed into the shared venv during setup.",
    )
    # Imports the setup crew actually executed successfully (the real
    # proof the env works), e.g. "import torch", "from sam2.build_sam import build_sam2".
    verified_imports: list[str] = Field(
        default_factory=list,
        description="Imports the setup crew ran successfully as a smoke test.",
    )
    # Heavyweight files fetched during setup and where they landed, so the
    # worker can reuse rather than re-download them.
    downloaded_artifacts: list[str] = Field(
        default_factory=list,
        description="Weights/data downloaded during setup, with their locations.",
    )
    # Honest list of anything still missing or risky the execution crew
    # must work around (gated weights, GPU-only ops, unresolved errors).
    known_gaps: list[str] = Field(
        default_factory=list,
        description="Remaining blockers/risks the execution crew must handle.",
    )
    # Free-form guidance for the execution crew: commands that worked,
    # important paths, and any workaround the human suggested.
    notes: str = Field(
        default="",
        description="Free-form guidance to the execution crew.",
    )
    # Record of the human exchanges during setup (question → answer) so the
    # handover and the saved chain capture how a blocker was resolved.
    human_consults: list[str] = Field(
        default_factory=list,
        description="Questions asked to the human during setup and their answers.",
    )


def format_env_report_for_worker(env: EnvReport) -> str:
    """Render an ``EnvReport`` as the preamble prepended to the worker's input.

    Kept as a plain string builder (no SDK) so it is unit-testable and so
    the execution worker receives the setup state as ordinary prompt text.
    """
    lines = [
        "ENVIRONMENT REPORT (from the setup crew — the venv is already prepared):",
        f"- venv_ready: {env.venv_ready}",
    ]
    if env.installed_packages:
        lines.append(f"- installed: {', '.join(env.installed_packages)}")
    if env.verified_imports:
        lines.append(f"- verified imports: {', '.join(env.verified_imports)}")
    if env.downloaded_artifacts:
        lines.append(f"- downloaded: {', '.join(env.downloaded_artifacts)}")
    if env.known_gaps:
        lines.append("- KNOWN GAPS to work around: " + "; ".join(env.known_gaps))
    if env.human_consults:
        lines.append("- human guidance so far: " + " | ".join(env.human_consults))
    if env.notes:
        lines.append(f"- notes: {env.notes}")
    lines.append(
        "\nThose dependencies are already installed in the shared venv — do not "
        "reinstall them unless an import actually fails. Now answer the question below."
    )
    return "\n".join(lines)


SETUP_INSTRUCTIONS = """\
You are the ENVIRONMENT SETUP ENGINEER. Your ONLY job is to get the shared
per-paper Python virtual environment ready to run this paper's code, then
report what you did. You do NOT answer the research question — a separate
execution agent does that next, using your report.

You have NO configuration file. Discover everything from the repository and,
when needed, from the human.

WORKFLOW
────────
1. ORIENT — Call read_paper() briefly, then map the repo. Look specifically
   for install instructions: README, requirements.txt, requirements*.txt,
   setup.py, pyproject.toml, environment.yml, Makefile, INSTALL/docs. Use
   list_repo_files(), find_repo_files(), and read_repo_file().

2. INSPECT — Call venv_status() to see what is already installed (the venv is
   shared across questions, so it may already be warm). Only install what is
   missing.

3. INSTALL — Install dependencies with execute_command("pip install ...",
   timeout=3600). Bare `pip` and `python` already route into the project venv;
   never use absolute interpreter paths. If the repo is a package (has
   setup.py / pyproject.toml) and its code is imported as a module, stage it
   and run `pip install -e .` so it registers.

4. FETCH (only if documented) — If the repo documents how to download weights
   or data (a script, a documented URL/command), run it. BUT if it requires a
   credential, token, license acceptance, or is huge/ambiguous, call
   ask_human BEFORE proceeding.

5. VERIFY — Prove the env works with small smoke tests:
   execute_command('python -c "import <pkg>; print(\\'ok\\')"'). Record each
   import that succeeds in verified_imports. This is the real evidence the
   handover is sound.

6. ASK WHEN STUCK — Call ask_human(question) whenever a person could unblock
   you: an ambiguous dependency/version (e.g. which torch/CUDA build), a gated
   or credentialed download, a needed workaround (e.g. "use the open model
   variant that needs no token"), or a go/no-go before an expensive step.
   Always state what you tried, the exact error, and 1-2 concrete options,
   then act on the reply.
   HARD RULE: a license acceptance, API token, credential, paywall, or gated
   download is ALWAYS a reason to call ask_human. NEVER record such an item in
   known_gaps (and never set venv_ready=false because of it) without calling
   ask_human about it first — the operator may have the token or a concrete
   workaround (e.g. an open, un-gated model variant).

REPORT (EnvReport)
──────────────────
- venv_ready: true only if the key imports the question will need actually
  succeeded; false if setup is blocked.
- installed_packages / verified_imports / downloaded_artifacts: only what you
  ACTUALLY did — never fabricate.
- known_gaps: be honest about anything still missing or risky (e.g. "default
  model weights are license-gated; use the open variant", "needs a GPU").
- notes: concrete guidance for the executor — working commands, key paths, and
  any workaround the human gave you.
- human_consults: each question you asked and the answer you got.

Do not run the paper's actual experiment or compute the answer — stop at a
verified, ready (or honestly-blocked) environment and report.
"""


_ASK_HUMAN_CARVEOUT = """\

  ASKING THE HUMAN (human-in-the-loop)
  ────────────────────────────────────
  You have an ask_human(question) tool, and an operator is usually watching.
  BEFORE you return a blocked EXECUTION_REQUIRED answer, if a human could
  plausibly unblock you, call ask_human first. Good reasons to ask:
    • a credential / token / gated resource is required (e.g. a license token);
    • there is a known workaround you should be told about (e.g. "use the open
      V2 model variant, which needs no token");
    • the question text or a referenced path is ambiguous and the repo does
      not disambiguate it;
    • a go/no-go before an expensive download or a long training run.
  When you ask: state exactly what you tried, the exact error, and 1-2 concrete
  options. The reply arrives as "HUMAN REPLY: ...". INCORPORATE it and continue
  — if told to use a different API/model/flag, actually run it and observe the
  result. Do NOT ask for things you can determine yourself by reading the repo.
  Only fall back to EXECUTION_REQUIRED if the human cannot unblock you either.

  HARD RULE: a missing license / token / credential, or a gated / paywalled
  download, is ALWAYS an ask_human situation. You MUST call ask_human BEFORE
  returning any blocked or EXECUTION_REQUIRED answer that is caused by a token,
  license, credential, paywall, or gated resource — even if the environment
  report already lists it as a known gap. The operator may hold the token or
  know a workaround (e.g. an open model variant). Returning EXECUTION_REQUIRED
  for such a cause without first calling ask_human is a failure.
"""


# Execution-worker prompt = the existing improved ReAct prompt plus the
# ask-the-human carve-out appended.  We append (rather than edit the
# baseline) so react_agent.py stays untouched and the HITL behaviour is an
# obvious additive block.
_DATA_FABRICATION_BAN = """\

  DATA-FABRICATION BAN (overrides the synthesis carve-out above)
  ─────────────────────────────────────────────────────────────
  If a specific input file or dataset the question depends on is missing from the
  repo, you MUST NOT invent, regenerate, or substitute it to produce a
  data-dependent result — i.e. any statistic, metric, score, accuracy, prediction,
  MSE/loss, embedding, or count whose value depends on the actual data. That yields
  a confident but meaningless number. Instead, call ask_human to decide (e.g. "the
  pre-generated data is missing; regenerate it from the repo's own generator with the
  stated seed, or block?"), and if the human does not authorise it, report blocked
  with blocker_type="missing_input". The narrow synthesis carve-out still applies ONLY
  to tools whose output does not depend on input content (e.g. a padding tool whose
  result depends only on a target length)."""


EXECUTION_HITL_INSTRUCTIONS = (
    REACT_INSTRUCTIONS_IMPROVED + _ASK_HUMAN_CARVEOUT + _DATA_FABRICATION_BAN
)


def create_setup_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the Stage-1 environment-setup engineer (emits an ``EnvReport``)."""
    return Agent(
        name="Environment Setup Engineer (HITL)",
        instructions=SETUP_INSTRUCTIONS,
        tools=_HITL_TOOLS,
        model=model,
        output_type=EnvReport,
    )


def create_execution_agent_hitl(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the Stage-2 ReAct execution worker with the ask-human carve-out.

    Same tools and ``ReActAnswer`` output as the baseline improved worker,
    plus ``ask_human``.  Suitable as a ``worker_factory`` for
    ``orchestration.run_with_critic`` (it accepts a single ``model`` arg).
    """
    return Agent(
        name="ReAct Execution Worker (HITL)",
        instructions=EXECUTION_HITL_INSTRUCTIONS,
        tools=_HITL_TOOLS,
        model=model,
        output_type=ReActAnswer,
    )


TRIAGE_INSTRUCTIONS = """\
You are the REPO SCOUT. Decide, up front, whether answering the user's question
requires running code, and gather a quick map of the repository for whoever answers
next. You do NOT answer the question, and you NEVER install or run anything.

STEPS
─────
1. Call read_paper() briefly, and explore the repo (list_repo_files / find_repo_files /
   search_repo / read_repo_file) just enough to (a) describe what the repo is and
   contains, and (b) locate the files/dirs relevant to the question.
2. Decide needs_execution:
   • FALSE (read-only) — conceptual/text questions answerable from the paper or repo text
     alone: "summarise", "what is this repo/paper about", "explain the method", "what is
     the main contribution", "what does module X do".
   • TRUE — anything requiring you to run code to get the answer: "run", "compute",
     "predict", "reproduce", "train", "generate", "what is the value/accuracy/MSE/count/
     shape", "process this file".
   When genuinely unsure, prefer TRUE (better to set up needlessly than to answer a
   compute question from text); call ask_human only if a quick steer would settle it.
3. Emit a TriageReport: needs_execution, a one-line rationale, a short repo_overview, and
   the relevant_paths you found.

Do not install dependencies, write files, or execute commands — that is a later stage's job.
"""


def create_triage_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the Stage-0 Repo Scout (routes read-only vs execution; emits ``TriageReport``)."""
    return Agent(
        name="Repo Scout (HITL triage)",
        instructions=TRIAGE_INSTRUCTIONS,
        tools=_READING_TOOLS,
        model=model,
        output_type=TriageReport,
    )


READONLY_INSTRUCTIONS = """\
You answer a READ-ONLY question about a paper and its repository — no code is needed.

You have ONLY reading tools (read_paper, list/find/resolve/search/read repo) and
ask_human. You CANNOT and MUST NOT run code, install anything, or execute commands.

Ground every claim in what you actually read: call read_paper() and read the relevant repo
files, then answer clearly and concisely, listing the paper sections / repo files you used
in `sources`. Produce the normal Thought/Action/Observation/Reflection chain for the reads
you do, then the final_answer.

Set answer_status="answered" and blocker_type="none" for a normal read-only answer. ONLY if
the question genuinely turns out to require executing code (it was mis-routed here) set
answer_status="blocked" and final_answer to "EXECUTION_REQUIRED — <reason>". Do not
fabricate; if the paper/repo does not contain the answer, say so honestly.
"""


def create_readonly_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the read-only answerer (reading tools + ask_human only; emits ``ReActAnswer``)."""
    return Agent(
        name="Read-only Answerer (HITL)",
        instructions=READONLY_INSTRUCTIONS,
        tools=_READING_TOOLS,
        model=model,
        output_type=ReActAnswer,
    )
