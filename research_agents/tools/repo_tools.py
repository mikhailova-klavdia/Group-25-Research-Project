# Read-only tools for inspecting a local repository.
#
# Three tools are exposed to the agent:
#   list_repo_files  — see what files exist
#   search_repo      — grep for a term across readable files
#   read_repo_file   — read a single file by relative path
#
# All tools get the repo path from the SDK context, so the LLM
# only ever works with relative paths inside repo/.
#
# Safety: binary files, large files, and ignored directories
# (.git, node_modules, etc.) are filtered out. Path traversal
# outside the repo root is blocked.

from pathlib import Path

from agents import RunContextWrapper, function_tool

from research_agents.project import ResearchContext


# --- Filtering rules ---

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
IGNORED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".class",
    ".jar",
    ".lock",
}
MAX_FILE_BYTES = 200_000  # skip files bigger than ~200 KB
MAX_LISTED_FILES = 400
MAX_MATCHES = 50
MAX_LINE_LENGTH = 240


# --- Internal helpers ---


def _resolve_repo_root(repo_path: str | Path) -> Path:
    root = Path(repo_path).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {repo_path}")
    return root


def _is_text_file(path: Path) -> bool:
    """Quick check: if the first 4 KB contain a null byte, it's probably binary."""
    try:
        with path.open("rb") as handle:
            chunk = handle.read(4096)
    except OSError as exc:
        raise ValueError(f"Unable to read file: {path}") from exc

    return b"\x00" not in chunk


def _should_skip_file(path: Path) -> bool:
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True
    if path.stat().st_size > MAX_FILE_BYTES:
        return True
    return not _is_text_file(path)


def _iter_repo_files(root: Path):
    """Walk the repo tree, skipping ignored dirs and non-text files."""
    for current_root, dirnames, filenames in root.walk():
        dirnames[:] = [dirname for dirname in dirnames if dirname not in IGNORED_DIRS]

        current_path = Path(current_root)
        for filename in sorted(filenames):
            path = current_path / filename
            if filename in {".DS_Store"}:
                continue
            if _should_skip_file(path):
                continue
            yield path


# --- Pure functions (used directly by tests) ---


def list_repo_files_text(repo_path: str | Path) -> str:
    root = _resolve_repo_root(repo_path)
    files = []
    omitted = 0

    for path in _iter_repo_files(root):
        relative = path.relative_to(root).as_posix()
        if len(files) >= MAX_LISTED_FILES:
            omitted += 1
            continue
        files.append(relative)

    if not files:
        return f"No readable text files found under {root}"

    lines = [f"Readable repository files under {root}:"]
    lines.extend(files)
    if omitted:
        lines.append(f"... {omitted} additional files omitted")
    return "\n".join(lines)


def search_repo_text(repo_path: str | Path, query: str) -> str:
    root = _resolve_repo_root(repo_path)
    needle = query.strip().lower()
    if not needle:
        raise ValueError("Search query must not be empty")

    matches: list[str] = []

    for path in _iter_repo_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

        for line_number, line in enumerate(lines, start=1):
            if needle not in line.lower():
                continue
            preview = line.strip()
            if len(preview) > MAX_LINE_LENGTH:
                preview = preview[: MAX_LINE_LENGTH - 3] + "..."
            relative = path.relative_to(root).as_posix()
            matches.append(f"{relative}:{line_number}: {preview}")
            if len(matches) >= MAX_MATCHES:
                return "\n".join(
                    [
                        f"Search results for {query!r} under {root}:",
                        *matches,
                        f"... search truncated after {MAX_MATCHES} matches",
                    ]
                )

    if not matches:
        return f"No matches found for {query!r} under {root}"

    return "\n".join([f"Search results for {query!r} under {root}:", *matches])


def read_repo_file_text(repo_path: str | Path, relative_path: str) -> str:
    root = _resolve_repo_root(repo_path)
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("relative_path must be relative to the repo/ directory")

    # Block path traversal (e.g. ../../../etc/passwd)
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested file is outside the repo/ directory") from exc

    if not resolved.exists():
        raise ValueError(f"Requested file does not exist: {relative_path}")
    if not resolved.is_file():
        raise ValueError(f"Requested path is not a file: {relative_path}")
    if _should_skip_file(resolved):
        raise ValueError(f"Requested file is not available for reading: {relative_path}")

    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = resolved.read_text(encoding="utf-8", errors="ignore")

    return f"Contents of {resolved}:\n{content}"


# --- SDK tool wrappers (thin layer over the pure functions above) ---


@function_tool
def list_repo_files(context: RunContextWrapper[ResearchContext]) -> str:
    """List readable text files in the local project repository."""
    return list_repo_files_text(context.context.repo_path)


@function_tool
def search_repo(context: RunContextWrapper[ResearchContext], query: str) -> str:
    """Search readable repository files for a text query.

    Args:
        query: Case-insensitive text to search for.
    """
    return search_repo_text(context.context.repo_path, query)


@function_tool
def read_repo_file(context: RunContextWrapper[ResearchContext], relative_path: str) -> str:
    """Read a single text file from the repository.

    Args:
        relative_path: Path to a file relative to repo/.
    """
    return read_repo_file_text(context.context.repo_path, relative_path)
