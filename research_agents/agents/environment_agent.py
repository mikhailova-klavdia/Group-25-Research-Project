"""Dedicated Environment Agent for the multi-agent pipeline.

The Environment Agent is a first-class pipeline stage that runs **before**
extraction, execution, and reasoning begin.  It owns the entire
dependency-preparation lifecycle:

  DISCOVER  → locate dependency metadata in the repo
  INSPECT   → parse required packages; check the shared per-paper venv
  INSTALL   → install missing packages and attempt conflict resolution
  VERIFY    → run lightweight import smoke-tests
  REPORT    → emit a typed ``EnvironmentReport`` downstream agents consume

By separating environment work into its own agent, later agents start from
a documented baseline instead of rediscovering setup state at execution
time.  The report also provides an audit trail: when the worker fails for
an environment reason, the record explains why.

This agent intentionally has NO hypothesis-generation, NO paper reading,
and NO experiment execution — it is scoped exclusively to environment
preparation.  Reading the paper or reasoning about experiments is the
worker's job.
"""

from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.exec_tools import (
    execute_command,
    list_workspace_files,
    venv_status,
    write_file,
)
from research_agents.tools.repo_tools import (
    find_repo_files,
    list_repo_files,
    read_repo_file,
    search_repo,
)


# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------


class EnvironmentReport(BaseModel):
    """Typed handover from the Environment Agent to downstream agents.

    Every field is populated from real tool calls — not static inference.
    Downstream agents consume this as a verified starting point for
    execution; they should not re-install packages already listed in
    ``installed_packages`` or re-check imports in ``verified_imports``.
    """

    # Machine-readable readiness gate used by orchestration to decide
    # whether to proceed to extraction/execution or halt.
    #   ready   — all required packages installed, imports verified
    #   partial — environment works for most tasks but has known gaps
    #   blocked — a hard blocker prevents meaningful execution
    status: Literal["ready", "partial", "blocked"] = Field(
        description="Overall readiness: ready / partial / blocked"
    )

    # Dependency files discovered in the repo, e.g. "requirements.txt",
    # "pyproject.toml".  Tells downstream agents which files were found
    # and analysed; empty list means the repo has no dependency metadata.
    detected_dependency_files: list[str] = Field(
        default_factory=list,
        description="Dependency/setup files found in the repo.",
    )

    # Packages the agent extracted from all dependency files combined.
    # Does not include transitive dependencies — only what was listed.
    required_packages: list[str] = Field(
        default_factory=list,
        description="Packages declared in dependency files (top-level only).",
    )

    # Packages present in the shared venv after the agent ran.  Populated
    # from ``pip list`` or ``uv pip list`` output, not from assumptions.
    installed_packages: list[str] = Field(
        default_factory=list,
        description="Packages confirmed installed in the shared venv.",
    )

    # Packages the agent attempted to install but could not satisfy.
    # Each entry is the package name, optionally with the error reason.
    missing_packages: list[str] = Field(
        default_factory=list,
        description="Packages that could not be installed with reasons.",
    )

    # Version conflicts, ABI incompatibilities, or build failures observed
    # during the install phase.  Each entry is a one-line description.
    conflicts: list[str] = Field(
        default_factory=list,
        description="Version conflicts or build failures encountered.",
    )

    # Shell commands actually executed (pip install, import checks, etc.)
    # so the record is fully reproducible and auditable.
    setup_commands_run: list[str] = Field(
        default_factory=list,
        description="Commands run during the environment setup phase.",
    )

    # Import statements that were tested and the pass/fail result, e.g.
    # "import torch — OK", "import esm — FAILED: No module named esm".
    # These are the only hard evidence that packages actually work.
    validation_checks: list[str] = Field(
        default_factory=list,
        description="Import smoke-tests run with pass/fail results.",
    )

    # Hard blockers that prevent any meaningful execution.  May include
    # missing GPU, missing system libraries, license-gated weights, or
    # Python version incompatibility.
    blockers: list[str] = Field(
        default_factory=list,
        description="Hard blockers preventing execution.",
    )

    # Platform requirements detected from the repo (e.g. "CUDA GPU",
    # "Linux only", "R >= 4.0").  Populated from README or setup files.
    platform_requirements: list[str] = Field(
        default_factory=list,
        description="Platform/system requirements detected (GPU, OS, R, etc.).",
    )

    # Python version detected from the venv or config.
    python_version: str | None = Field(
        default=None,
        description="Python version in the shared venv, e.g. '3.9.17'.",
    )

    # Free-form guidance for the worker: workarounds that worked, paths
    # that matter, and any version-pinning that was necessary.
    notes: str = Field(
        default="",
        description="Free-form guidance for downstream agents.",
    )


# ---------------------------------------------------------------------------
# Pure helper functions (unit-testable without the SDK)
# ---------------------------------------------------------------------------

#: Filenames that indicate a Python dependency specification.
DEPENDENCY_FILE_NAMES: frozenset[str] = frozenset({
    "requirements.txt",
    "requirements-dev.txt",
    "requirements_dev.txt",
    "requirements-test.txt",
    "requirements-base.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "environment.yml",
    "environment.yaml",
    "Pipfile",
    "Pipfile.lock",
    "conda.yaml",
    "conda.yml",
})

#: Keywords in setup text that indicate non-Python platform requirements.
_PLATFORM_KEYWORDS: list[tuple[str, str]] = [
    ("cuda", "CUDA GPU required"),
    ("gpu", "GPU required"),
    ("nvidia", "NVIDIA GPU required"),
    ("linux", "Linux OS required"),
    ("bioconda", "bioconda channel required (conda install)"),
    ("docker", "Docker required"),
    ("singularity", "Singularity/Apptainer required"),
    ("r language", "R language required"),
    ("r >= ", "R language required"),
    ("bioconductor", "Bioconductor (R) required"),
    ("java", "Java runtime required"),
    ("samtools", "samtools system binary required"),
    ("pysam", "pysam requires htslib (Linux/macOS build)"),
]


def classify_dependency_file(filename: str) -> str:
    """Return a human-readable label for a dependency file.

    Used when building the agent's prompt context so it knows how to parse
    each file it finds.  Unrecognised files return 'unknown'.
    """
    name = filename.lower().split("/")[-1]
    if name in ("requirements.txt", "requirements-dev.txt",
                "requirements_dev.txt", "requirements-test.txt",
                "requirements-base.txt"):
        return "pip-requirements"
    if name == "pyproject.toml":
        return "pyproject-toml"
    if name in ("setup.py", "setup.cfg"):
        return "setup-py"
    if name in ("environment.yml", "environment.yaml", "conda.yaml", "conda.yml"):
        return "conda-environment"
    if name in ("pipfile", "pipfile.lock"):
        return "pipenv"
    return "unknown"


def detect_platform_requirements(text: str) -> list[str]:
    """Scan free-form text for non-Python platform requirement keywords.

    Checks README or setup file content for words that indicate the code
    needs something beyond pure pip: a GPU, a specific OS, R, Java, etc.
    Returns a deduplicated list of human-readable requirement strings.

    This is a heuristic scan, not a parser — it catches the most common
    blockers without attempting to understand the document structure.
    """
    lower = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    for keyword, label in _PLATFORM_KEYWORDS:
        if keyword in lower and label not in seen:
            found.append(label)
            seen.add(label)
    return found


def format_environment_report_for_worker(report: EnvironmentReport) -> str:
    """Render an ``EnvironmentReport`` as prompt preamble for the worker.

    Called by the orchestration layer to prepend environment context to
    the worker's input.  Pure string builder so it is unit-testable and
    the worker receives environment state as ordinary text.
    """
    lines = [
        "ENVIRONMENT REPORT (from the Environment Agent — do not repeat this setup):",
        f"  status          : {report.status}",
        f"  python_version  : {report.python_version or 'unknown'}",
    ]
    if report.detected_dependency_files:
        lines.append(f"  dep files found : {', '.join(report.detected_dependency_files)}")
    if report.installed_packages:
        lines.append(f"  installed       : {', '.join(report.installed_packages[:20])}"
                     + (" …" if len(report.installed_packages) > 20 else ""))
    if report.missing_packages:
        lines.append(f"  MISSING         : {', '.join(report.missing_packages)}")
    if report.conflicts:
        lines.append(f"  CONFLICTS       : {'; '.join(report.conflicts)}")
    if report.validation_checks:
        lines.append("  validation      :")
        for check in report.validation_checks:
            lines.append(f"    {check}")
    if report.platform_requirements:
        lines.append(f"  platform reqs   : {', '.join(report.platform_requirements)}")
    if report.blockers:
        lines.append("  BLOCKERS        :")
        for b in report.blockers:
            lines.append(f"    ✗ {b}")
    if report.notes:
        lines.append(f"  notes           : {report.notes}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

ENVIRONMENT_AGENT_INSTRUCTIONS = """\
You are the Environment Agent. Your only job is to prepare the shared
per-paper Python virtual environment so downstream agents can run code
without worrying about missing packages or environment state.

You produce a structured ``EnvironmentReport`` at the end. Every field in
that report must be backed by real tool calls — no guessing.

═══════════════════════════════════════════════════════════════
PHASE 1 — DISCOVER
═══════════════════════════════════════════════════════════════

Find every dependency/setup file in the repo:

1. Call list_repo_files() to get the full file tree.
2. Look for: requirements.txt, requirements-dev.txt, pyproject.toml,
   setup.py, setup.cfg, environment.yml, conda.yaml, Pipfile.
3. Call find_repo_files() with patterns ".txt", ".toml", ".cfg", ".yml"
   to catch files in subdirectories.
4. Search the README for setup instructions:
   search_repo("installation") then search_repo("dependencies").
5. Record every dependency file you found in detected_dependency_files.

═══════════════════════════════════════════════════════════════
PHASE 2 — INSPECT
═══════════════════════════════════════════════════════════════

Read every dependency file you found:

1. Call read_repo_file() for each file.
2. Parse the package names from the file (just top-level names, no
   transitive deps).  Populate required_packages.
3. Check the current venv state: call venv_status().
   - Note the Python version for python_version.
   - Note what is already installed for installed_packages.
4. Compute missing_packages = required_packages − installed_packages.
5. Scan the README text for GPU/CUDA/Linux/R/Docker mentions. Add any
   found to platform_requirements.

═══════════════════════════════════════════════════════════════
PHASE 3 — INSTALL
═══════════════════════════════════════════════════════════════

Install missing packages:

1. For pip-installable packages: run
   execute_command("pip install <pkg1> <pkg2> ...", timeout=3600)
   Record each command in setup_commands_run.
2. If a package fails to install:
   - Try once with a version relaxation (drop the version pin).
   - If it still fails, add it to missing_packages with the error reason.
   - Add it to blockers ONLY if it is critical for the question.
3. If the environment.yml requires conda: note this in platform_requirements
   as "conda environment required" and add to blockers if pip is
   insufficient.
4. Do NOT attempt to install packages that need compilation (e.g. pysam
   on Windows) — add them to blockers immediately with the reason.

═══════════════════════════════════════════════════════════════
PHASE 4 — VERIFY
═══════════════════════════════════════════════════════════════

Run import smoke-tests to confirm packages actually work:

1. For each package in installed_packages (up to 10 most important):
   write a small Python script that imports the package:
     write_file("check_imports.py", "import <pkg>; print('OK')")
   then execute_command("python check_imports.py", timeout=30).
2. Record each result in validation_checks, e.g.:
   "import torch — OK (cuda: False)" or "import esm — FAILED".
3. If a core package fails its import check, add it to blockers.

═══════════════════════════════════════════════════════════════
PHASE 5 — REPORT
═══════════════════════════════════════════════════════════════

Set the status field:
  "ready"   — all required packages installed and imports verified.
  "partial" — most packages work but some optional ones are missing or
              platform requirements (GPU, Linux) are unmet.
  "blocked" — a hard blocker means the downstream question cannot run
              at all (missing critical dep, wrong Python version, etc.).

Populate notes with any workarounds you applied, important paths, or
advice for the worker (e.g. "use numpy<2 — numpy 2.x breaks this repo").

SCOPE LIMITS
────────────
- Do NOT attempt to answer the benchmark question.
- Do NOT run the paper's actual experiment scripts.
- Do NOT download large model weights (>100 MB) — record them as blockers.
- Maximum 40 tool calls total across all phases.
- If you exceed 35 tool calls, finalize immediately with what you have.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_environment_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the Environment Agent.

    Tools are scoped to what environment preparation actually needs:
    - repo reading tools to find and parse dependency files
    - venv_status to inspect the current shared venv
    - execute_command + write_file to install packages and run checks
    - list_workspace_files for checking workspace state

    Notably absent: read_paper, stage_repo_path, stage_paper_artifact.
    Those belong to the worker — the environment agent only prepares
    the venv, it does not stage files for experiment execution.
    """
    return Agent(
        name="Environment Agent",
        instructions=ENVIRONMENT_AGENT_INSTRUCTIONS,
        tools=[
            # Repo reading — find and parse dependency files
            list_repo_files,
            find_repo_files,
            read_repo_file,
            search_repo,
            # Venv inspection
            venv_status,
            # Package installation and import verification
            execute_command,
            write_file,
            list_workspace_files,
        ],
        model=model,
        output_type=EnvironmentReport,
    )
