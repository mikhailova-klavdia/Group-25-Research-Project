# Defines the project workspace layout and validates it.
#
# Each project lives under papers/<slug>/ and must contain:
#   paper.pdf  — the research paper
#   repo/      — the cloned repository for that paper
#
# Optionally a `.research_config.toml` at the paper root pins the Python
# version and seed packages for the per-paper shared venv, and lists
# one-time setup scripts / Python warmups that should run once during venv
# creation (e.g. to fetch model weights up-front so they don't eat into
# each question's execution budget):
#
#   [venv]
#   python_version = "3.9"
#   seed_packages = ["torch==1.13.1"]
#
#   [setup]
#   # Bash scripts run once from <project_dir>/repo/ after the venv is
#   # created, with the venv on PATH.  Use for weight downloads.
#   download_scripts = ["weights/download.sh"]
#   # Python one-liners run via the venv's interpreter.  Use to pre-warm
#   # framework caches (e.g. ESM-2 pretrained weights).
#   warmup_imports = [
#       "from esm.pretrained import esm2_t33_650M_UR50D; esm2_t33_650M_UR50D()",
#   ]
#   # Seconds.  Defaults to 3600 (the same MAX_TIMEOUT as execute_command).
#   download_timeout = 3600

import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    # Type-only import to avoid a runtime cycle: hitl.py imports
    # ResearchContext from this module at import time.
    from research_agents.hitl import HumanChannel, Reporter


# Default cap on each setup-step subprocess.  Weight downloads are the
# motivating use case (PPLM pulls ~hundreds of MB of Google Drive blobs
# via gdown), and 1 hour is the same ceiling execute_command applies to
# arbitrary agent-run commands — keeping them aligned avoids surprises.
_DEFAULT_SETUP_TIMEOUT = 3600


@dataclass
class ResearchContext:
    """Holds resolved paths for a single research project.

    This is passed as the SDK context object to Runner.run_sync(),
    so every tool can access these paths at runtime without the
    LLM ever seeing the file system layout.

    The venv is PER-PAPER (under ``project_dir/.venv/``), not per-run.
    Multiple questions against the same paper reuse the same venv, so
    deps install once instead of once per question.  Each question still
    gets its own ``workspace_path`` under ``runs/<run-id>/workspace/`` for
    output isolation.

    ``artifacts_path`` is also per-paper.  It is for reusable heavyweight
    outputs (downloaded weights, generated pickles/arrays) that should
    survive across question workspaces without polluting ``repo/``.
    """

    project_dir: Path
    paper_path: Path
    repo_path: Path
    run_id: str
    run_dir: Path
    workspace_path: Path
    venv_path: Path
    artifacts_path: Path
    # Optional human-in-the-loop chat channel; None on headless/batch runs.
    human: "HumanChannel | None" = field(default=None)
    # Optional progress reporter for streaming output; None on headless/batch runs.
    reporter: "Reporter | None" = field(default=None)
    # Cached repo overview from the first triage of a hitl_main session; None
    # on batch runs and before the first question in an interactive session.
    # Set by _run_triage_stage so subsequent questions skip re-reading the paper.
    session_overview: str | None = field(default=None)

    # Optional human-in-the-loop chat channel.  The interactive CLI
    # (``hitl_main``) sets this so the ``ask_human`` tool can reach the
    # operator; it stays ``None`` on headless/batch runs, where ask_human
    # degrades to "proceed autonomously".  Additive and defaulted, so every
    # existing construction of ResearchContext is unaffected.
    human: "HumanChannel | None" = None

    # Optional progress reporter.  The interactive CLI sets this so the team can
    # stream friendly stage/step updates while it works; ``None`` on
    # headless/batch runs means total silence (no behaviour change there).
    # Additive and defaulted, like ``human``.
    reporter: "Reporter | None" = None

    # Complete log of operator assistance for this run: one entry per
    # ``ask_human`` round-trip ({"question", "answer"}), appended at the tool
    # boundary by ``ask_human`` itself.  Recorded here — not reconstructed from
    # the worker's self-reported chain — so the saved record has an accurate
    # count and transcript of every help request even when the worker omits the
    # call from its chain.  Empty whenever ask_human is never used (the default
    # for every headless/non-assisted run), so existing constructions and the
    # saved schema for those runs are unaffected.
    human_interactions: list[dict[str, str]] = field(default_factory=list)

    # Optional path to a per-paper help file (``AGENT_HINTS.md``, placed alongside the repo)
    # carrying steering tips for this paper's tasks.  Read by the ``read_help`` tool and used
    # by the README-assisted teams; ``None`` (or the file simply absent) on every other run,
    # where ``read_help`` reports that no help is attached.  Additive and defaulted, so
    # existing constructions are unaffected.
    help_path: "Path | None" = None

    # Set True by the README-assisted teams when they inject the help file's text into the
    # worker's input. The injected preamble is not stored in the chain (the saved question is
    # kept clean), so this flag lets the saved record attest that help was actually provided
    # for this question. False on every non-assisted run.
    help_injected: bool = False


def _venv_bin_name() -> str:
    """Return the venv's scripts-directory name for the current platform.

    ``uv venv`` (like the stdlib ``venv`` module) creates ``Scripts/`` on
    Windows and ``bin/`` everywhere else.  Anywhere we need to invoke or
    PATH-prepend the venv's binaries, route through this helper instead
    of hardcoding ``"bin"`` — the previous hardcoded ``"bin"`` was the
    Windows-path bug flagged in the multi-agent refactor plan.
    """
    return "Scripts" if sys.platform == "win32" else "bin"


def _python_exe_name() -> str:
    """Return the Python interpreter filename for the current platform."""
    return "python.exe" if sys.platform == "win32" else "python"


def _find_python_in_venv(venv_path: Path) -> Path | None:
    """Return the python interpreter inside a venv, or None if no venv there.

    Checks the platform-correct location first, then falls back to the
    other layout so a venv created on a different host (CI, bind mount,
    user moving between macOS and Windows) still gets detected.
    """
    candidates = [
        venv_path / _venv_bin_name() / _python_exe_name(),
        venv_path / "bin" / "python",
        venv_path / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_paper_config(project_dir: Path) -> dict:
    """Read ``papers/<slug>/.research_config.toml`` if present, else ``{}``.

    The config carries per-paper venv settings (Python version + seed
    packages).  Validation is lazy — missing keys, missing file, or a
    malformed TOML file fall back to defaults rather than aborting the
    run.  Malformed TOML emits a warning so the user notices.
    """
    config_path = project_dir / ".research_config.toml"
    if not config_path.is_file():
        return {}
    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        print(f"Warning: failed to parse {config_path}: {exc}", file=sys.stderr)
        return {}


def _python_major_minor(python_exe: Path) -> str | None:
    """Return ``"X.Y"`` for the given Python executable, or ``None`` on failure.

    Used to validate that an existing venv matches the config's pinned
    Python version before we reuse it.  Short timeout (10 s) because the
    only thing we run is a one-liner that prints two integers.
    """
    try:
        result = subprocess.run(
            [
                str(python_exe),
                "-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None


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


def _run_setup_scripts(venv_path: Path, repo_path: Path | None, config: dict | None) -> None:
    """Run one-time setup commands after a venv is freshly created.

    The ``[setup]`` table of ``.research_config.toml`` exposes two lists:

      * ``download_scripts`` — relative paths (relative to ``repo_path``)
        to bash scripts that fetch model weights or other heavyweight
        artifacts.  We invoke ``bash <script>`` from ``cwd=repo_path``
        with the venv's binary directory prepended to ``PATH`` and
        ``VIRTUAL_ENV`` set, so the script can ``pip install gdown`` /
        ``python -m gdown ...`` without first finding the venv itself.
      * ``warmup_imports`` — Python one-liners run via the venv's
        interpreter to pre-populate caches (e.g. ``fair-esm`` downloads
        ESM-2 weights on first call, and we'd rather pay that cost once
        at setup time than once per question).

    Failures are deliberately non-fatal: a flaky download or a missing
    optional script must not brick the entire eval.  We print a clear
    warning to stderr so the operator can investigate, and the per-
    question loop's own retry logic still has a chance to recover.

    ``repo_path`` may be ``None`` when the helper is called outside the
    full ``resolve_project`` flow (e.g. some unit tests).  In that case
    ``download_scripts`` is skipped because their interpretation depends
    on the repo root.
    """
    config = config or {}
    setup_cfg = config.get("setup", {}) or {}
    download_scripts: list[str] = list(setup_cfg.get("download_scripts", []))
    warmup_imports: list[str] = list(setup_cfg.get("warmup_imports", []))
    timeout = int(setup_cfg.get("download_timeout", _DEFAULT_SETUP_TIMEOUT))

    if not download_scripts and not warmup_imports:
        return

    # Compose the env the subprocesses run under so a fresh shell finds
    # the venv first on PATH and tools like `python` / `pip` route into
    # it without absolute paths.
    venv_bin = venv_path / _venv_bin_name()
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv_path)
    env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"

    for script in download_scripts:
        if repo_path is None:
            print(
                f"Warning: skipping setup.download_scripts entry '{script}' "
                "because no repo_path was provided.",
                file=sys.stderr,
            )
            continue
        script_path = (repo_path / script).resolve()
        if not script_path.is_file():
            print(
                f"Warning: setup.download_scripts entry '{script}' does not exist "
                f"under {repo_path}; skipping.",
                file=sys.stderr,
            )
            continue
        try:
            subprocess.run(
                ["bash", str(script_path)],
                cwd=str(repo_path),
                env=env,
                check=True,
                timeout=timeout,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            print(
                f"Warning: setup.download_scripts entry '{script}' failed: {exc}. "
                "Continuing — the per-question loop may still recover.",
                file=sys.stderr,
            )

    python_exe = _find_python_in_venv(venv_path)
    if warmup_imports and python_exe is None:
        print(
            f"Warning: cannot run setup.warmup_imports because no python interpreter "
            f"was found in {venv_path}.",
            file=sys.stderr,
        )
        return

    for oneliner in warmup_imports:
        try:
            subprocess.run(
                [str(python_exe), "-c", oneliner],
                cwd=str(repo_path) if repo_path is not None else None,
                env=env,
                check=True,
                timeout=timeout,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            print(
                f"Warning: setup.warmup_imports entry failed ({oneliner!r}): {exc}. "
                "Continuing — the per-question loop may still recover.",
                file=sys.stderr,
            )


def _ensure_venv(
    venv_path: Path,
    config: dict | None = None,
    repo_path: Path | None = None,
    apply_setup: bool = True,
) -> None:
    """Idempotently create or reuse a per-paper venv.

    Behavior:
      * If a venv already exists at ``venv_path`` and the config places
        no version constraint, reuse it.  Subsequent questions benefit
        from the warm install cache.
      * If a venv exists and the config pins ``python_version``, verify
        the existing venv matches.  Mismatch → raise ``ValueError`` so
        the user makes an explicit call (rm -rf the venv) rather than
        silently destroying installed packages.
      * If no venv exists, create one with ``uv venv --seed [--python X.Y]``,
        then install any ``seed_packages`` (e.g. ``torch==1.13.1`` for
        PPLM) so the first question against a fresh paper has the right
        baseline.

    ``uv venv --seed`` pre-installs pip/setuptools so the agent's first
    ``pip install`` call works without bootstrap steps.  Seed packages
    are paper-specific install hints declared in
    ``.research_config.toml``.
    """
    config = config or {}
    venv_cfg = config.get("venv", {}) or {}
    expected_python: str | None = venv_cfg.get("python_version")
    seed_packages: list[str] = list(venv_cfg.get("seed_packages", []))

    existing = _find_python_in_venv(venv_path)
    if existing is not None:
        if expected_python is None:
            print(f"[venv] Reusing existing venv at {venv_path}")
            return  # no version constraint → reuse whatever's there
        actual = _python_major_minor(existing)
        if actual == expected_python:
            print(f"[venv] Reusing existing venv at {venv_path} (Python {actual})")
            return  # version matches → reuse
        raise ValueError(
            f"Venv at {venv_path} is Python {actual}, but "
            f".research_config.toml requests {expected_python}. "
            f"Remove the venv (rm -rf {venv_path}) and re-run to "
            "recreate it with the requested version."
        )

    print(f"[venv] Creating new venv at {venv_path}")
    cmd = ["uv", "venv", "--seed"]
    if expected_python:
        # `uv venv --python 3.9` selects the interpreter; uv downloads it
        # via its managed-Python feature if no matching system Python is
        # available, so the user doesn't need to install 3.9 themselves.
        cmd.extend(["--python", expected_python])
    cmd.append(str(venv_path))
    subprocess.run(cmd, check=True, capture_output=True)

    if seed_packages:
        # Install seed_packages directly into the new venv via uv pip.
        # 30-minute timeout because torch installs can take many minutes
        # on a cold wheel cache.
        python_exe = _find_python_in_venv(venv_path)
        if python_exe is None:
            raise RuntimeError(f"Created venv at {venv_path} but no python interpreter found")
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python_exe),
                *seed_packages,
            ],
            check=True,
            capture_output=True,
            timeout=1800,
        )

    # One-time setup steps (weight downloads, framework cache warmups).
    # These run AFTER the seed-package install so a setup script can
    # rely on, e.g., `gdown` already being available in the venv.  Any
    # failure here is logged as a warning rather than raised — the
    # agent's per-question loop has its own retry, and we don't want a
    # transient download glitch to brick the whole eval.
    #
    # Gated by ``apply_setup`` so teams that want the colleague's exact
    # baseline behavior (``worker-critic``) can skip the setup step even
    # when a paper's config has a ``[setup]`` block.  Only the
    # ``worker-critic-plus`` team passes ``apply_setup=True``.
    if apply_setup:
        _run_setup_scripts(venv_path, repo_path, config)


def resolve_project(project_dir: str, apply_setup: bool = False) -> ResearchContext:
    """Validate a project directory and return a ResearchContext.

    The venv now lives at ``<project_dir>/.venv/`` (per-paper, shared
    across questions) instead of ``<project_dir>/runs/<run-id>/.venv/``
    (the previous per-question layout).  First call for a paper creates
    the venv; subsequent calls reuse it.  Workspaces and run outputs
    stay per-run under ``runs/<run-id>/``.

    A sibling ``<project_dir>/.artifacts/`` directory is also created for
    reusable files that future runs can stage back into their workspace.

    Setting ``apply_setup=True`` opts into the per-paper
    ``.research_config.toml`` ``[setup]`` table (download scripts +
    warmup imports run once at venv-creation time).  Default ``False``
    so callers that haven't opted in see the colleague's baseline venv-
    setup behavior — only the ``worker-critic-plus`` team passes True.

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

    # Per-paper reusable artifact cache.  Unlike run workspaces, this is
    # intentionally shared across questions for large downloads and
    # generated files that later questions can reuse.
    artifacts_path = root / ".artifacts"
    artifacts_path.mkdir(exist_ok=True)

    # Per-paper shared venv.  Read optional config first so we can pin
    # the Python version and pre-install paper-specific packages.  The
    # repo path is passed through so [setup] scripts (e.g. PPLM's
    # weights/download.sh) can run from the correct cwd, but they only
    # actually fire when the caller passed apply_setup=True.
    config = _read_paper_config(root)
    venv_path = root / ".venv"
    _ensure_venv(venv_path, config=config, repo_path=repo_path, apply_setup=apply_setup)

    return ResearchContext(
        project_dir=root,
        paper_path=paper_path,
        repo_path=repo_path,
        run_id=run_id,
        run_dir=run_dir,
        workspace_path=workspace_path,
        venv_path=venv_path,
        artifacts_path=artifacts_path,
        # Per-paper steering file, if a README-assisted runner placed one here.
        help_path=root / "AGENT_HINTS.md",
    )


def fresh_workspace(base: ResearchContext) -> ResearchContext:
    """Create a fresh per-question workspace under the same project root.

    Used by ``hitl_main`` to give each session question its own isolated
    workspace (run_id, run_dir, workspace_path) without recreating the
    shared venv, re-reading the config, or re-running setup scripts.
    Human, reporter, and session_overview are NOT carried over — the
    caller attaches them explicitly after this call.
    """
    run_id = _create_run_id()
    run_dir = base.project_dir / "runs" / run_id
    run_dir.mkdir(parents=True)
    workspace_path = run_dir / "workspace"
    workspace_path.mkdir()
    return ResearchContext(
        project_dir=base.project_dir,
        paper_path=base.paper_path,
        repo_path=base.repo_path,
        run_id=run_id,
        run_dir=run_dir,
        workspace_path=workspace_path,
        venv_path=base.venv_path,
        artifacts_path=base.artifacts_path,
        help_path=base.help_path,
    )


def delete_venv(venv_path: Path) -> None:
    """Remove a per-paper venv so the next run rebuilds it from scratch.

    Used by react_main's ``--fresh-venv-per-question`` mode, where each
    benchmark question must start from a clean Python environment (the HITL
    setup engineer is part of what's being evaluated, so it has to rebuild the
    venv every time rather than inherit a warm one from a previous question).

    Model weights deliberately live OUTSIDE the venv — framework caches under
    ``~/.cache`` / ``~/Library/Caches`` and the paper's ``repo/`` checkpoint
    directories — so wiping ``<project>/.venv`` resets the interpreter and every
    installed package without discarding any downloaded weights (which are large
    and, for some papers, flaky to re-fetch).

    A missing venv is a no-op, so callers can invoke this unconditionally both
    before and after a run without first checking whether the path exists.
    """
    if venv_path.exists():
        shutil.rmtree(venv_path)
