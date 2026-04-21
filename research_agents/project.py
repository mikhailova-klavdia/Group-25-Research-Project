# Defines the project workspace layout and validates it.
#
# Each project lives under papers/<slug>/ and must contain:
#   paper.pdf  — the research paper
#   repo/      — the cloned repository for that paper

import subprocess
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4


@dataclass
class ResearchContext:
    """Holds resolved paths for a single research project.

    This is passed as the SDK context object to Runner.run_sync(),
    so every tool can access these paths at runtime without the
    LLM ever seeing the file system layout.
    """

    project_dir: Path
    paper_path: Path
    repo_path: Path
    run_id: str
    run_dir: Path
    workspace_path: Path
    venv_path: Path


def _create_run_id() -> str:
    """Generate a unique, sortable run ID.

    Format is ``<UTC-timestamp>-<uuid4-hex8>`` (e.g.
    ``20260420T143022-a1b2c3d4``).  The timestamp prefix keeps runs
    chronologically sortable when you ``ls runs/``; the 8-char uuid
    suffix disambiguates runs launched in the same second (e.g. two
    benchmark questions fired in parallel).  UTC is used so that runs
    launched from different machines / timezones still sort correctly.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _ensure_venv(venv_path: Path) -> None:
    """Create an isolated Python venv for this run if one isn't there yet.

    We use a fresh venv per run so that:
      * experiments from one paper (e.g. conflicting torch versions) cannot
        contaminate another paper's run,
      * a second run against the same paper starts clean — no stale installs
        from a prior attempt,
      * the system Python is never touched; users don't need to maintain
        or trust a shared project env.

    ``uv venv --seed`` creates the venv and pre-installs ``pip`` /
    ``setuptools`` so the agent's first ``pip install`` call works without
    bootstrap steps.  ``capture_output=True`` keeps uv's progress noise out
    of the CLI output; ``check=True`` lets exceptions propagate if venv
    creation fails (e.g. uv not on PATH).
    """
    # Check for the interpreter on BOTH Unix (`bin/python`) and Windows
    # (`Scripts/python.exe`) layouts.  Primary dev environment is macOS, but
    # a Windows user with uv installed should still get idempotent behaviour.
    if (venv_path / "bin" / "python").exists():
        return
    if (venv_path / "Scripts" / "python.exe").exists():
        return

    subprocess.run(
        ["uv", "venv", "--seed", str(venv_path)],
        check=True,
        capture_output=True,
    )


def resolve_project(project_dir: str) -> ResearchContext:
    """Validate a project directory and return a ResearchContext.

    Raises ValueError if the directory is missing, or if paper.pdf
    or repo/ are not where they should be.
    """
    root = Path(project_dir).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"Project directory does not exist: {project_dir}")
    if not root.is_dir():
        raise ValueError(f"Project path is not a directory: {project_dir}")

    paper_path = root / "paper.pdf"
    if not paper_path.is_file():
        raise ValueError(f"Missing paper.pdf in project directory: {root}")

    repo_path = root / "repo"
    if not repo_path.is_dir():
        raise ValueError(f"Missing repo/ directory in project directory: {root}")

    runs_dir = root / "runs"
    runs_dir.mkdir(exist_ok=True)

    run_id = _create_run_id()
    run_dir = runs_dir / run_id
    run_dir.mkdir()

    workspace_path = run_dir / "workspace"
    workspace_path.mkdir()

    venv_path = run_dir / ".venv"
    _ensure_venv(venv_path)

    return ResearchContext(
        project_dir=root,
        paper_path=paper_path,
        repo_path=repo_path,
        run_id=run_id,
        run_dir=run_dir,
        workspace_path=workspace_path,
        venv_path=venv_path,
    )
