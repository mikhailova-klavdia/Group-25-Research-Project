# Read-only tools for inspecting a local repository.
#
# Five tools are exposed to the agent:
#   list_repo_files    — see readable text files
#   find_repo_files    — search filenames, including binary/large artifacts
#   resolve_repo_path  — map question paths to real repo paths/candidates
#   search_repo        — grep for a term across readable files
#   read_repo_file     — read a single file by relative path
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
# Files above this size are almost always data dumps, pretrained weights, or
# generated assets — rarely source code the agent would benefit from reading.
# 200 KB comfortably covers typical Python / C++ / docs files while keeping
# the token budget for `read_repo_file` bounded and predictable.
MAX_FILE_BYTES = 200_000  # skip files bigger than ~200 KB

# Upper bound on entries returned by `list_repo_files`.  Large monorepos
# (e.g. sam2, grf) easily have thousands of files; showing all of them
# drowns the agent and wastes tokens.  400 is enough to orient in most
# research repos; anything beyond that, the agent should narrow with search.
MAX_LISTED_FILES = 400

# Upper bound on matches returned by `search_repo`.  Generous grep hits on
# common terms (e.g. "import") quickly blow past any useful signal; cap at
# 50 and instruct the agent to refine the query when it hits the ceiling.
MAX_MATCHES = 50

# Upper bound for filename/artifact searches.  This can be slightly larger
# than content grep because one filename line is cheap, but still bounded so
# checkpoint-heavy or generated-output-heavy repos do not drown the worker.
MAX_FILE_MATCHES = 100

# Preview trimmed per matching line.  240 chars fits most single-line code
# or prose matches without forcing the reader to scroll horizontally and
# without swamping the result list.
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
    """Quick check: if the first 4 KB contain a null byte, it's probably binary.

    This is the same heuristic `git` uses to decide whether a file is binary.
    It's not perfect — some text encodings can contain nulls — but for the
    file types we actually care about (source code, docs, configs, CSVs) it
    has near-zero false positives and is dramatically cheaper than invoking
    `file(1)` or sniffing with a MIME library.  4 KB is enough to catch
    truly-binary files while still being trivially fast even on large trees.
    """
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
        # `dirnames[:] = ...` is the canonical os.walk / Path.walk idiom for
        # pruning subtrees during iteration.  Reassigning `dirnames` (without
        # the slice) would bind a NEW local name; the walker checks the SAME
        # list object after yielding, so it wouldn't notice the swap.  The
        # `[:]` slice mutates the list in place, which the walker DOES see —
        # meaning ignored directories (`.git`, `.venv`, `node_modules`, ...)
        # are never descended into, saving both time and memory on large
        # trees.
        dirnames[:] = [dirname for dirname in dirnames if dirname not in IGNORED_DIRS]

        current_path = Path(current_root)
        for filename in sorted(filenames):
            path = current_path / filename
            if filename in {".DS_Store"}:
                continue
            try:
                skip = _should_skip_file(path)
            except (ValueError, OSError):
                # An unreadable entry (broken symlink, permission error, a file
                # that vanished mid-walk, a special/device file) must NOT abort
                # the whole listing — skip just that file.  Previously the
                # ValueError raised by _is_text_file propagated up and made
                # `list_repo_files` fail entirely (observed on the grf repo).
                continue
            if skip:
                continue
            yield path


def _iter_repo_paths(root: Path):
    """Walk repo files, including binary and large artifacts.

    `list_repo_files` and `search_repo` intentionally hide large/binary
    files because the worker cannot read them as text.  Filename discovery
    has the opposite goal: surface weights, pickles, spreadsheets, FASTA,
    and generated arrays so the worker can stage or execute against them.
    """
    for current_root, dirnames, filenames in root.walk():
        dirnames[:] = [dirname for dirname in dirnames if dirname not in IGNORED_DIRS]

        current_path = Path(current_root)
        for filename in sorted(filenames):
            if filename == ".DS_Store":
                continue
            yield current_path / filename


def _format_size(num_bytes: int) -> str:
    """Return a compact human-readable byte size for artifact listings."""
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{num_bytes} B"


def _artifact_line(root: Path, path: Path) -> str:
    """Format one repo artifact candidate with size and readability hints."""
    relative = path.relative_to(root).as_posix()
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    try:
        readable_text = _is_text_file(path) and size <= MAX_FILE_BYTES
    except ValueError:
        readable_text = False
    kind = "text" if readable_text else "artifact"
    return f"{relative} [{kind}, {_format_size(size)}]"


def _path_exists_inside(root: Path, relative_path: str) -> Path | None:
    """Return a resolved repo path if relative_path exists inside root."""
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved if resolved.exists() else None


def _normalise_question_path(question_path: str) -> str:
    """Clean common quoting and separator noise from a path in a prompt."""
    return question_path.strip().strip("\"'`").replace("\\", "/").strip("/")


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


def find_repo_files_text(
    repo_path: str | Path,
    pattern: str,
    include_binary: bool = True,
) -> str:
    """Search repo filenames/paths, including large and binary artifacts.

    This complements `search_repo_text`, which greps only readable text
    files.  Research repos often keep the answerability-critical assets as
    `.pth`, `.pt`, `.pkl`, `.npy`, `.xlsx`, or FASTA/TSV files; those must
    be visible even when they are too large or binary to read directly.
    """
    root = _resolve_repo_root(repo_path)
    needle = pattern.strip().lower()
    if not needle:
        raise ValueError("File search pattern must not be empty")

    matches: list[str] = []
    for path in _iter_repo_paths(root):
        relative = path.relative_to(root).as_posix()
        if needle not in relative.lower() and needle not in path.name.lower():
            continue
        if not include_binary:
            try:
                if not _is_text_file(path):
                    continue
            except ValueError:
                continue
        matches.append(_artifact_line(root, path))
        if len(matches) >= MAX_FILE_MATCHES:
            return "\n".join(
                [
                    f"Filename results for {pattern!r} under {root}:",
                    *matches,
                    f"... search truncated after {MAX_FILE_MATCHES} matches",
                ]
            )

    if not matches:
        return f"No filenames matched {pattern!r} under {root}"

    return "\n".join([f"Filename results for {pattern!r} under {root}:", *matches])


def resolve_repo_path_text(repo_path: str | Path, question_path: str) -> str:
    """Resolve a path copied from a benchmark question to repo candidates.

    Benchmark prompts often include abstract notebook paths or prefix paths
    with the repo/package name.  This helper performs deterministic recovery
    before the worker gives up: exact path, one-segment prefix strip,
    basename match, and stem match.  It returns evidence, not a guess.
    """
    root = _resolve_repo_root(repo_path)
    raw = _normalise_question_path(question_path)
    if not raw:
        raise ValueError("question_path must not be empty")

    lines = [f"Resolving question path {question_path!r} under {root}:"]

    exact = _path_exists_inside(root, raw)
    if exact is not None:
        lines.append(f"exact: {_artifact_line(root, exact)}")
        return "\n".join(lines)

    parts = Path(raw).parts
    stripped = "/".join(parts[1:]) if len(parts) > 1 else ""
    if stripped:
        stripped_match = _path_exists_inside(root, stripped)
        if stripped_match is not None:
            lines.append(f"prefix-stripped: {_artifact_line(root, stripped_match)}")
            return "\n".join(lines)

    basename = Path(raw).name
    stem = Path(raw).stem
    candidates: list[str] = []
    seen: set[str] = set()

    for path in _iter_repo_paths(root):
        relative = path.relative_to(root).as_posix()
        if path.name == basename:
            seen.add(relative)
            candidates.append(f"basename: {_artifact_line(root, path)}")
        if len(candidates) >= MAX_FILE_MATCHES:
            break

    if not candidates and stem:
        for path in _iter_repo_paths(root):
            relative = path.relative_to(root).as_posix()
            if relative in seen:
                continue
            if stem.lower() in path.stem.lower() or stem.lower() in path.name.lower():
                seen.add(relative)
                candidates.append(f"stem: {_artifact_line(root, path)}")
            if len(candidates) >= MAX_FILE_MATCHES:
                break

    if candidates:
        lines.extend(candidates)
        if len(candidates) >= MAX_FILE_MATCHES:
            lines.append(f"... candidates truncated after {MAX_FILE_MATCHES} matches")
        return "\n".join(lines)

    tried = [raw]
    if stripped:
        tried.append(stripped)
    lines.append(f"No repo path resolved. Tried exact/prefix paths: {', '.join(tried)}")
    lines.append(f"No filename or stem candidates found for basename {basename!r}.")
    return "\n".join(lines)


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
    # Directory paths get their own error branch because the agent
    # sometimes passes a directory when it meant to explore it — the
    # generic "not a file" message was observed to confuse the model
    # into giving up; pointing it at list_repo_files is the recovery
    # path we want it to take.
    if resolved.is_dir():
        raise ValueError(
            f"Requested path is a directory, not a file: {relative_path}. "
            f"Use list_repo_files to see which files exist under repo/."
        )
    if not resolved.is_file():
        raise ValueError(f"Requested path is not a regular file: {relative_path}")
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
def find_repo_files(
    context: RunContextWrapper[ResearchContext],
    pattern: str,
    include_binary: bool = True,
) -> str:
    """Search repo filenames/paths, including binary and large artifacts.

    Args:
        pattern: Filename, suffix, stem, or path fragment to search for.
        include_binary: Whether to include binary/large files in results.
    """
    return find_repo_files_text(context.context.repo_path, pattern, include_binary)


@function_tool
def resolve_repo_path(context: RunContextWrapper[ResearchContext], question_path: str) -> str:
    """Resolve a path from the question to real repo path candidates.

    Args:
        question_path: Path string copied from the benchmark question.
    """
    return resolve_repo_path_text(context.context.repo_path, question_path)


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
