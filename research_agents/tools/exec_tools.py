# Tools for writing files and executing commands.
#
# Nine tools are exposed to the agent:
#   write_file             — create or overwrite a file in workspace/
#   stage_repo_path        — copy a repo file or directory into workspace/
#   execute_command        — run a shell command in workspace/
#   list_workspace_files   — see what files exist in workspace/
#   read_workspace_file    — read a file the agent produced in workspace/
#   list_paper_artifacts   — see reusable files cached for this paper
#   stage_paper_artifact   — copy a cached artifact into workspace/
#   cache_workspace_artifact — save reusable workspace output for later runs
#   venv_status            — inspect the shared per-paper venv before installs
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

from research_agents.project import ResearchContext, _find_python_in_venv, _venv_bin_name
from research_agents.tools.repo_tools import IGNORED_DIRS

# Cap for `write_file`.  Paper-reproducing helpers are usually small
# scripts; something over 500 KB is almost certainly an LLM hallucinating
# a giant dataset inline instead of generating or downloading it.
MAX_WRITE_BYTES = 500_000  # reject files bigger than ~500 KB

# Trimming cap for stdout/stderr returned from `execute_command`.  50 KB
# is enough to include error tracebacks and summary tables while keeping
# the agent's context window from being flooded by verbose training logs.
MAX_OUTPUT_BYTES = 50_000  # truncate stdout/stderr beyond this

# Cap for `read_workspace_file`.  Matches the repo-side limit so the
# agent has the same mental model for "readable size" on either side.
MAX_READ_BYTES = 200_000  # truncate workspace file reads beyond this

# Default subprocess timeout.  120 seconds covers most small-scale
# experiments (loading a model, running a handful of predictions) while
# still catching runaway commands quickly during development.
DEFAULT_TIMEOUT = 120

# Hard upper bound on timeout the agent can request.  Dependency installs
# for torch/ESM-style research stacks can take 3-15 minutes on a cold
# cache, so the ceiling is one hour while the default stays short for
# ordinary commands.
MAX_TIMEOUT = 3600

# Matches repo_tools.MAX_LISTED_FILES; see that comment for rationale.
MAX_LISTED_FILES = 400


# --- Pure functions (used directly by tests) ---


def write_file_text(workspace_path: str | Path, relative_path: str, content: str) -> str:
    """Write content to a file inside the workspace directory."""
    root = Path(workspace_path).resolve()

    # Strip a leading "workspace/" the agent sometimes prepends by mistake,
    # which would otherwise create a workspace/workspace/ double-nesting.
    for prefix in ("workspace/", "workspace\\"):
        if relative_path.startswith(prefix):
            relative_path = relative_path[len(prefix):]
            break

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
        # The detailed error is model-facing: it nudges the agent to search
        # instead of hallucinating a path after a failed stage attempt.
        filename = Path(relative_path).name
        return (
            f"ERROR: '{relative_path}' does not exist in the repo. "
            f"Do NOT proceed with staging. "
            f"Call resolve_repo_path('{relative_path}') or find_repo_files('{filename}') "
            f"to find if this file exists at a different path, then stage "
            f"the correct path instead."
        )
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


def _resolve_relative_root(root: Path, relative_path: str, root_label: str) -> Path:
    """Resolve a relative path under root and reject traversal/absolute paths."""
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"relative_path must be relative to the {root_label}/ directory")

    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Requested path is outside the {root_label}/ directory") from exc
    return resolved


def _copy_file_or_directory(source: Path, destination: Path) -> str:
    """Copy source to destination and return whether it was a file or directory."""
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*IGNORED_DIRS),
        )
        return "directory"

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return "file"


def execute_command_text(
    workspace_path: str | Path,
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    venv_path: str | Path | None = None,
    env_vars: dict[str, str] | None = None,
) -> str:
    """Run a shell command with cwd set to the given directory.

    If venv_path is provided, its platform-specific scripts directory is
    prepended to PATH so that python/pip resolve to the isolated venv.
    """
    root = Path(workspace_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")

    # Clamp so a single command cannot exceed the hard per-command ceiling.
    timeout = min(timeout, MAX_TIMEOUT)

    env = os.environ.copy()
    # Prepend the run's venv/bin to PATH so bare `python` / `pip` calls in
    # the agent's commands route into the isolated venv automatically.  The
    # agent doesn't have to know the absolute path — this is what makes
    # "pip install x" Just Work without the agent writing `.venv/bin/pip`.
    # VIRTUAL_ENV is also set for packaging tools that check for it (uv,
    # pip itself) to recognise the activated env.
    if venv_path is not None:
        venv_bin = str(Path(venv_path).resolve() / _venv_bin_name())
        env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(Path(venv_path).resolve())
    # env_vars carries the RESEARCH_* locators plus a PYTHONPATH that
    # already has the repo root prepended; see the `execute_command` SDK
    # wrapper below for where that's assembled.
    if env_vars:
        env.update(env_vars)

    # `shell=True` is deliberate: the agent writes shell-style commands
    # (pipes, redirects, `cd && run`) and we want those to Just Work.  The
    # usual warning about `shell=True` — untrusted user input becomes
    # command injection — is accepted here because the "user" issuing
    # commands IS the agent, running inside a run-scoped workspace + venv,
    # and we're the sole operator.  Don't copy this pattern into a
    # multi-tenant or web-facing tool without rethinking the threat model.
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
    except subprocess.TimeoutExpired as exc:
        # When a command times out, subprocess stashes whatever it had
        # already read from the child's stdout/stderr pipes on the
        # exception.  Surfacing that partial output is often the only
        # way to tell whether the command was stuck in an infinite loop,
        # waiting on network, or genuinely long-running — so we include
        # it in the error message rather than dropping it silently.
        # Both fields may be None or bytes; decode defensively.
        partial_stdout = exc.stdout
        partial_stderr = exc.stderr
        if isinstance(partial_stdout, bytes):
            partial_stdout = partial_stdout.decode("utf-8", errors="replace")
        if isinstance(partial_stderr, bytes):
            partial_stderr = partial_stderr.decode("utf-8", errors="replace")

        parts = [f"Command timed out after {timeout} seconds:\n  {command}"]
        if partial_stdout and partial_stdout.strip():
            if len(partial_stdout) > MAX_OUTPUT_BYTES:
                partial_stdout = (
                    partial_stdout[:MAX_OUTPUT_BYTES]
                    + f"\n[stdout truncated at {MAX_OUTPUT_BYTES} bytes]"
                )
            parts.append(f"\nSTDOUT (partial):\n{partial_stdout}")
        if partial_stderr and partial_stderr.strip():
            if len(partial_stderr) > MAX_OUTPUT_BYTES:
                partial_stderr = (
                    partial_stderr[:MAX_OUTPUT_BYTES]
                    + f"\n[stderr truncated at {MAX_OUTPUT_BYTES} bytes]"
                )
            parts.append(f"\nSTDERR (partial):\n{partial_stderr}")
        return "\n".join(parts)

    stdout = result.stdout
    stderr = result.stderr

    # Truncate early so one noisy training log doesn't blow past the
    # agent's context window.  The trailing marker tells the agent
    # truncation happened, so it can narrow its next investigation.
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


def list_paper_artifacts_text(artifacts_path: str | Path) -> str:
    """List reusable paper-level artifacts available to this run.

    The artifact cache intentionally includes binary and large files,
    because its main purpose is to persist weights, pickles, arrays, and
    similar assets across per-question workspaces.
    """
    root = Path(artifacts_path).resolve()
    if not root.is_dir():
        return f"Paper artifact directory does not exist: {artifacts_path}"

    files = []
    omitted = 0
    for current_root, dirnames, filenames in root.walk():
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in IGNORED_DIRS]
        current_path = Path(current_root)
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            size = path.stat().st_size
            line = f"{relative} ({size} bytes)"
            if len(files) >= MAX_LISTED_FILES:
                omitted += 1
                continue
            files.append(line)

    if not files:
        return "Paper artifact cache is empty."

    lines = ["Paper artifacts:"]
    lines.extend(files)
    if omitted:
        lines.append(f"... {omitted} additional files omitted")
    return "\n".join(lines)


def stage_paper_artifact_text(
    artifacts_path: str | Path,
    workspace_path: str | Path,
    relative_path: str,
    destination_path: str | None = None,
) -> str:
    """Copy a reusable paper artifact into the current workspace."""
    artifacts_root = Path(artifacts_path).resolve()
    workspace_root = Path(workspace_path).resolve()
    if not artifacts_root.is_dir():
        raise ValueError(f"Paper artifact directory does not exist: {artifacts_path}")
    if not workspace_root.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")

    source = _resolve_relative_root(artifacts_root, relative_path, ".artifacts")
    if not source.exists():
        return (
            f"ERROR: artifact '{relative_path}' does not exist. Call list_paper_artifacts() first."
        )

    if destination_path is None:
        destination_candidate = Path(relative_path)
    else:
        destination_candidate = Path(destination_path)
        if destination_candidate.is_absolute():
            raise ValueError("destination_path must be relative to the workspace/ directory")
    destination = _resolve_relative_root(
        workspace_root, destination_candidate.as_posix(), "workspace"
    )

    copied_kind = _copy_file_or_directory(source, destination)
    relative_destination = destination.relative_to(workspace_root).as_posix()
    return f"Staged artifact {copied_kind} {relative_path} into workspace/{relative_destination}"


def cache_workspace_artifact_text(
    workspace_path: str | Path,
    artifacts_path: str | Path,
    relative_path: str,
    destination_path: str | None = None,
) -> str:
    """Copy a reusable workspace output into the paper-level artifact cache."""
    workspace_root = Path(workspace_path).resolve()
    artifacts_root = Path(artifacts_path).resolve()
    if not workspace_root.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")
    artifacts_root.mkdir(parents=True, exist_ok=True)

    source = _resolve_relative_root(workspace_root, relative_path, "workspace")
    if not source.exists():
        return f"ERROR: workspace path '{relative_path}' does not exist. Call list_workspace_files() first."

    if destination_path is None:
        destination_candidate = Path(relative_path)
    else:
        destination_candidate = Path(destination_path)
        if destination_candidate.is_absolute():
            raise ValueError("destination_path must be relative to the .artifacts/ directory")
    destination = _resolve_relative_root(
        artifacts_root,
        destination_candidate.as_posix(),
        ".artifacts",
    )

    copied_kind = _copy_file_or_directory(source, destination)
    relative_destination = destination.relative_to(artifacts_root).as_posix()
    return f"Cached workspace {copied_kind} {relative_path} into .artifacts/{relative_destination}"


def read_workspace_file_text(workspace_path: str | Path, relative_path: str) -> str:
    """Read a file from the workspace directory."""
    root = Path(workspace_path).resolve()

    # Same leading-prefix strip as write_file_text.
    for prefix in ("workspace/", "workspace\\"):
        if relative_path.startswith(prefix):
            relative_path = relative_path[len(prefix):]
            break

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


def venv_status_text(venv_path: str | Path) -> str:
    """Summarise the shared per-paper venv for dependency planning.

    The ReAct worker calls this before installing packages so it can
    reuse already-installed dependencies across questions for the same
    paper.  Output is intentionally compact: Python version, disk free
    space, and a capped freeze-style package list.
    """
    root = Path(venv_path).resolve()
    python_exe = _find_python_in_venv(root)
    if python_exe is None:
        return f"Venv does not exist or has no Python interpreter: {root}"

    try:
        version = subprocess.run(
            [str(python_exe), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        python_version = (version.stdout or version.stderr).strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        python_version = "unknown"

    try:
        packages = subprocess.run(
            [str(python_exe), "-m", "pip", "list", "--format=freeze"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        package_lines = sorted(line for line in packages.stdout.splitlines() if line.strip())
    except (OSError, subprocess.TimeoutExpired):
        package_lines = []

    disk_root = root if root.exists() else root.parent
    usage = shutil.disk_usage(disk_root)
    free_gib = usage.free / (1024**3)

    lines = [
        f"Venv path: {root}",
        f"Python: {python_version}",
        f"Free disk: {free_gib:.1f} GiB",
        f"Installed packages: {len(package_lines)}",
    ]
    if package_lines:
        shown = package_lines[:120]
        lines.extend(shown)
        omitted = len(package_lines) - len(shown)
        if omitted > 0:
            lines.append(f"... {omitted} additional packages omitted")
    return "\n".join(lines)


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
        timeout: Max seconds to wait (default 120, max 3600).
    """
    repo_path = context.context.repo_path.resolve()
    # Expose the key paths as RESEARCH_* env vars so commands the agent
    # generates can reference them without hard-coding absolute paths.
    # The agent's prompt documents these; they're the contract between
    # the runtime and any helper scripts the agent might write.
    env_vars = {
        "RESEARCH_PROJECT_PATH": str(context.context.project_dir.resolve()),
        "RESEARCH_REPO_PATH": str(repo_path),
        "RESEARCH_PAPER_PATH": str(context.context.paper_path.resolve()),
        "RESEARCH_RUN_PATH": str(context.context.run_dir.resolve()),
        "RESEARCH_WORKSPACE_PATH": str(context.context.workspace_path.resolve()),
        "RESEARCH_ARTIFACTS_PATH": str(context.context.artifacts_path.resolve()),
    }

    # Prepend the repo root to PYTHONPATH so `import <repo-package>` works
    # from the workspace without the agent having to replicate the repo
    # layout.  Any PYTHONPATH inherited from the parent process is kept
    # at the end (lower priority) so our prepending wins on name collisions.
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


@function_tool
def list_paper_artifacts(context: RunContextWrapper[ResearchContext]) -> str:
    """List reusable paper-level artifacts cached across question runs."""
    return list_paper_artifacts_text(context.context.artifacts_path)


@function_tool
def stage_paper_artifact(
    context: RunContextWrapper[ResearchContext],
    relative_path: str,
    destination_path: str | None = None,
) -> str:
    """Copy a cached paper artifact into the current run workspace.

    Args:
        relative_path: Path relative to .artifacts/.
        destination_path: Optional path relative to workspace/.
    """
    return stage_paper_artifact_text(
        context.context.artifacts_path,
        context.context.workspace_path,
        relative_path,
        destination_path,
    )


@function_tool
def cache_workspace_artifact(
    context: RunContextWrapper[ResearchContext],
    relative_path: str,
    destination_path: str | None = None,
) -> str:
    """Save a reusable workspace output into the paper artifact cache.

    Args:
        relative_path: Path relative to workspace/.
        destination_path: Optional path relative to .artifacts/.
    """
    return cache_workspace_artifact_text(
        context.context.workspace_path,
        context.context.artifacts_path,
        relative_path,
        destination_path,
    )


@function_tool
def venv_status(context: RunContextWrapper[ResearchContext]) -> str:
    """Inspect the shared per-paper venv before installing dependencies."""
    return venv_status_text(context.context.venv_path)
