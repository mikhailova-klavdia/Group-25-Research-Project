# Tools for writing files and executing commands.
#
# Five tools are exposed to the agent:
#   write_file           — create or overwrite a file in workspace/
#   stage_repo_path      — copy a repo file or directory into workspace/
#   execute_command      — run a shell command in workspace/
#   list_workspace_files — see what files exist in workspace/
#   read_workspace_file  — read a file the agent produced in workspace/
#
# New files are always written to workspace/. Commands always run from the
# current run workspace, never from the shared repo. The shared repo stays
# input-only; files or directories needed for execution must be staged into
# workspace/ first. All commands use an isolated venv created by uv so they
# never touch the system Python.

import os
import shutil
import subprocess
from pathlib import Path

from agents import RunContextWrapper, function_tool

from research_agents.project import ResearchContext
from research_agents.tools.repo_tools import IGNORED_DIRS

MAX_WRITE_BYTES = 500_000  # reject files bigger than ~500 KB
MAX_OUTPUT_BYTES = 50_000  # truncate stdout/stderr beyond this
MAX_READ_BYTES = 200_000   # truncate workspace file reads beyond this
DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600
MAX_LISTED_FILES = 400


# --- Pure functions (used directly by tests) ---


def write_file_text(workspace_path: str | Path, relative_path: str, content: str) -> str:
    """Write content to a file inside the workspace directory."""
    root = Path(workspace_path).resolve()

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("relative_path must be relative to the workspace/ directory")

    # Block path traversal.
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested path is outside the workspace/ directory") from exc

    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ValueError(f"File content exceeds the {MAX_WRITE_BYTES} byte limit")

    # Create parent directories if they don't exist.
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return f"Wrote {len(content)} characters to {relative_path}"


def stage_repo_path_text(
    repo_path: str | Path,
    workspace_path: str | Path,
    relative_path: str,
    destination_path: str | None = None,
) -> str:
    """Copy a repo file or directory into the workspace directory."""
    repo_root = Path(repo_path).resolve()
    workspace_root = Path(workspace_path).resolve()

    if not repo_root.is_dir():
        raise ValueError(f"Repository directory does not exist: {repo_path}")
    if not workspace_root.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")

    source_candidate = Path(relative_path)
    if source_candidate.is_absolute():
        raise ValueError("relative_path must be relative to the repo/ directory")

    source = (repo_root / source_candidate).resolve()
    try:
        source.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("Requested source path is outside the repo/ directory") from exc

    if not source.exists():
        raise ValueError(f"Requested source path does not exist: {relative_path}")
    if any(part in IGNORED_DIRS for part in source.relative_to(repo_root).parts):
        raise ValueError(f"Requested source path is not available for staging: {relative_path}")

    if destination_path is None:
        destination_candidate = source.relative_to(repo_root)
    else:
        destination_candidate = Path(destination_path)
        if destination_candidate.is_absolute():
            raise ValueError("destination_path must be relative to the workspace/ directory")

    destination = (workspace_root / destination_candidate).resolve()
    try:
        destination.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError("Requested destination path is outside the workspace/ directory") from exc

    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*IGNORED_DIRS),
        )
        copied_kind = "directory"
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_kind = "file"

    relative_destination = destination.relative_to(workspace_root).as_posix()
    return f"Staged {copied_kind} {relative_path} into workspace/{relative_destination}"


def execute_command_text(
    workspace_path: str | Path,
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    venv_path: str | Path | None = None,
    env_vars: dict[str, str] | None = None,
) -> str:
    """Run a shell command with cwd set to the given directory.

    If venv_path is provided, its bin/ directory is prepended to PATH
    so that python/pip resolve to the isolated venv.
    """
    root = Path(workspace_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")

    timeout = min(timeout, MAX_TIMEOUT)

    env = os.environ.copy()
    if venv_path is not None:
        venv_bin = str(Path(venv_path).resolve() / "bin")
        env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(Path(venv_path).resolve())
    if env_vars:
        env.update(env_vars)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds:\n  {command}"

    stdout = result.stdout
    stderr = result.stderr

    if len(stdout) > MAX_OUTPUT_BYTES:
        stdout = stdout[:MAX_OUTPUT_BYTES] + f"\n[stdout truncated at {MAX_OUTPUT_BYTES} bytes]"
    if len(stderr) > MAX_OUTPUT_BYTES:
        stderr = stderr[:MAX_OUTPUT_BYTES] + f"\n[stderr truncated at {MAX_OUTPUT_BYTES} bytes]"

    parts = [f"Exit code: {result.returncode}"]
    if stdout.strip():
        parts.append(f"\nSTDOUT:\n{stdout}")
    if stderr.strip():
        parts.append(f"\nSTDERR:\n{stderr}")

    return "\n".join(parts)


def list_workspace_files_text(workspace_path: str | Path) -> str:
    """List files in the workspace directory."""
    root = Path(workspace_path).resolve()
    if not root.is_dir():
        return f"Workspace directory does not exist: {workspace_path}"

    files = []
    omitted = 0

    for current_root, dirnames, filenames in root.walk():
        # Skip hidden dirs and common junk.
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]

        current_path = Path(current_root)
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            relative = (current_path / filename).relative_to(root).as_posix()
            if len(files) >= MAX_LISTED_FILES:
                omitted += 1
                continue
            files.append(relative)

    if not files:
        return "Workspace is empty — no files created yet."

    lines = ["Workspace files:"]
    lines.extend(files)
    if omitted:
        lines.append(f"... {omitted} additional files omitted")
    return "\n".join(lines)


def read_workspace_file_text(workspace_path: str | Path, relative_path: str) -> str:
    """Read a file from the workspace directory."""
    root = Path(workspace_path).resolve()

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("relative_path must be relative to the workspace/ directory")

    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested path is outside the workspace/ directory") from exc

    if not resolved.exists():
        raise ValueError(f"File does not exist in workspace: {relative_path}")
    if not resolved.is_file():
        raise ValueError(f"Path is not a file: {relative_path}")

    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = resolved.read_text(encoding="utf-8", errors="replace")

    if len(content) > MAX_READ_BYTES:
        content = content[:MAX_READ_BYTES] + f"\n[truncated at {MAX_READ_BYTES} bytes]"

    return f"Contents of workspace/{relative_path}:\n{content}"


# --- SDK tool wrappers ---


@function_tool
def write_file(
    context: RunContextWrapper[ResearchContext],
    relative_path: str,
    content: str,
) -> str:
    """Create or overwrite a file in the workspace directory.

    Args:
        relative_path: Path relative to workspace/ (e.g. "run_experiment.py").
        content: The full file content to write.
    """
    return write_file_text(context.context.workspace_path, relative_path, content)


@function_tool
def stage_repo_path(
    context: RunContextWrapper[ResearchContext],
    relative_path: str,
    destination_path: str | None = None,
) -> str:
    """Copy a repo file or directory into the current run workspace.

    Args:
        relative_path: Path to a repo file or directory relative to repo/.
        destination_path: Optional path relative to workspace/ where the
            staged content should be copied.
    """
    return stage_repo_path_text(
        context.context.repo_path,
        context.context.workspace_path,
        relative_path,
        destination_path,
    )


@function_tool
def execute_command(
    context: RunContextWrapper[ResearchContext],
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Run a shell command from the current run workspace and return its output.

    Args:
        command: The shell command to run (e.g. "python run_experiment.py").
        timeout: Max seconds to wait (default 120, max 600).
    """
    repo_path = context.context.repo_path.resolve()
    env_vars = {
        "RESEARCH_PROJECT_PATH": str(context.context.project_dir.resolve()),
        "RESEARCH_REPO_PATH": str(repo_path),
        "RESEARCH_PAPER_PATH": str(context.context.paper_path.resolve()),
        "RESEARCH_RUN_PATH": str(context.context.run_dir.resolve()),
        "RESEARCH_WORKSPACE_PATH": str(context.context.workspace_path.resolve()),
    }

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    env_vars["PYTHONPATH"] = (
        str(repo_path)
        if not existing_pythonpath
        else str(repo_path) + os.pathsep + existing_pythonpath
    )
    return execute_command_text(
        context.context.workspace_path,
        command,
        timeout,
        venv_path=context.context.venv_path,
        env_vars=env_vars,
    )


@function_tool
def list_workspace_files(context: RunContextWrapper[ResearchContext]) -> str:
    """List all files the agent has created in the workspace directory."""
    return list_workspace_files_text(context.context.workspace_path)


@function_tool
def read_workspace_file(
    context: RunContextWrapper[ResearchContext],
    relative_path: str,
) -> str:
    """Read a file from the workspace directory (output files, logs, CSVs, etc.).

    Args:
        relative_path: Path relative to workspace/ (e.g. "results/output.csv").
    """
    return read_workspace_file_text(context.context.workspace_path, relative_path)
