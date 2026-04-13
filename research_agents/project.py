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
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _ensure_venv(venv_path: Path) -> None:
    if (venv_path / "bin" / "python").exists():
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
