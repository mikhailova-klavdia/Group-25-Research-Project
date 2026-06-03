"""
run_eval.py — batch eval runner for tagged paper repos.

Resolves rank numbers → Papers/ folder → biorxiv URL → matching questions
from 300_questions.csv, wires up papers/<slug>/ workspace, and calls
react_main once per question so a running cost/token total can be printed
after each one completes.

Usage:
    uv run python run_eval.py --repos 1-21
    uv run python run_eval.py --repos 1 3 7
    uv run python run_eval.py --repos 1-5 8 --model gpt-5-mini-2025-08-07
    uv run python run_eval.py --repos 1-21 --team worker-critic-plus
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows so Unicode box-drawing characters
# in progress lines don't raise UnicodeEncodeError with cp1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Fixed paths (all relative to this file = project root) ─────────────────
ROOT         = Path(__file__).parent
PAPERS_DIR   = ROOT / "Papers"          # 74 tagged folders e.g. 01-3M-CyteOnto
AGENT_DIR    = ROOT / "papers"          # where react_main expects paper workspaces
QA_DIR       = ROOT / "question-answers"
QUESTIONS_CSV = (
    ROOT / "Paper2AgentBench" / "eval" / "100_compbio_repos" / "300_questions.csv"
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def parse_ranks(tokens: list[str]) -> list[int]:
    """Parse ['1-21', '3', '7'] into a sorted, deduplicated list of ints."""
    ranks: set[int] = set()
    for token in tokens:
        if "-" in token:
            lo, hi = token.split("-", 1)
            ranks.update(range(int(lo), int(hi) + 1))
        else:
            ranks.add(int(token))
    return sorted(ranks)


def find_folder(rank: int) -> Path | None:
    """Return the Papers/ subfolder whose name starts with the zero-padded rank."""
    prefix = f"{rank:02d}-"
    hits = [d for d in PAPERS_DIR.iterdir() if d.is_dir() and d.name.startswith(prefix)]
    return hits[0] if hits else None


def read_biorxiv_url(folder: Path) -> str | None:
    """Read biorxiv_link.txt; utf-8-sig strips the BOM if present."""
    f = folder / "biorxiv_link.txt"
    return f.read_text(encoding="utf-8-sig").strip() if f.exists() else None


def normalise_url(url: str) -> str:
    """Strip trailing version suffix (v1, v2 …) for robust matching."""
    return re.sub(r"v\d+$", "", url.rstrip("/"))


def extract_slug(folder_name: str) -> str:
    """
    '01-3M-CyteOnto'            → 'CyteOnto'
    '02-5M-GWAS-Epistasis-Bias' → 'GWAS-Epistasis-Bias'
    '22-17Md-mm2-ivh'           → 'mm2-ivh'
    Format: <rank>-<papernum><difficulty><tags>-<name…>
    """
    parts = folder_name.split("-", 2)
    return parts[2] if len(parts) >= 3 else folder_name


# Folder slug → QA JSON filename when they don't match directly.
_SLUG_JSON_OVERRIDE: dict[str, str] = {
    "metapointfinder": "METAPOINT.json",
}


def load_questions(biorxiv_url: str, slug: str) -> list[dict]:
    """
    Return questions for this repo.  CSV lookup is tried first (if the file
    exists); falls back to question-answers/<slug>.json so the runner keeps
    working after the upstream 300_questions.csv is no longer in the repo.
    """
    norm_target = normalise_url(biorxiv_url)
    id_prefix = slug.upper().replace("-", "_")

    if QUESTIONS_CSV.exists():
        matches = []
        with open(QUESTIONS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if normalise_url(row["biorxiv_link"]) == norm_target:
                    matches.append({
                        "id": f"{id_prefix}_{len(matches) + 1:03d}",
                        "question": row["question"],
                        "ground_truth": row["ground_truth"],
                    })
        if matches:
            return matches

    # Fall back to question-answers/<slug>.json (handles non-bio repos and
    # the case where 300_questions.csv has been removed from the repo).
    json_name = _SLUG_JSON_OVERRIDE.get(slug, f"{slug}.json")
    for candidate in (QA_DIR / json_name, QA_DIR / f"{slug.upper()}.json"):
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            return [
                {
                    "id": d.get("id", f"{id_prefix}_{i:03d}"),
                    "question": d["question"],
                    "ground_truth": d.get("ground_truth", ""),
                }
                for i, d in enumerate(data, 1)
            ]
    return []


def _junction(src: Path, dst: Path) -> None:
    """Create a Windows directory junction (no admin rights needed)."""
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
        check=True, capture_output=True,
    )


def link_item(src: Path, dst: Path) -> None:
    """
    Point dst at src without copying data.
    - Directories: junction on Windows, symlink elsewhere.
    - Files: symlink; copies as fallback if symlinks are blocked.
    Already-existing dst is left untouched.
    """
    if dst.exists() or dst.is_symlink():
        return
    src = src.resolve()
    if src.is_dir():
        if sys.platform == "win32":
            _junction(src, dst)
        else:
            dst.symlink_to(src)
    else:
        try:
            dst.symlink_to(src)
        except OSError:
            shutil.copy2(src, dst)


def setup_workspace(slug: str, source_folder: Path) -> Path:
    """
    Create papers/<slug>/ and wire repo/ + paper.pdf into it from the
    tagged Papers/ folder so react_main can find them without duplication.
    """
    paper_dir = AGENT_DIR / slug
    paper_dir.mkdir(parents=True, exist_ok=True)

    for name in ("repo", "paper.pdf"):
        src = source_folder / name
        if src.exists():
            link_item(src, paper_dir / name)

    return paper_dir


def write_qa_file(slug: str, questions: list[dict]) -> Path:
    """Write question-answers/<slug>.json in the standard format."""
    QA_DIR.mkdir(exist_ok=True)
    path = QA_DIR / f"{slug}.json"
    path.write_text(json.dumps(questions, indent=2), encoding="utf-8")
    return path


def read_latest_result(folder_name: str, entry_id: str) -> tuple[bool | None, int, int, float]:
    """
    Find the most recently written <entry_id>.json under papers/<folder_name>/runs/
    and return (correct, input_tokens, output_tokens, cost_usd).
    Token usage comes from the result JSON so it only reflects the current run.
    """
    hits = sorted(
        (AGENT_DIR / folder_name / "runs").glob(f"**/{entry_id}.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not hits:
        return None, 0, 0, 0.0
    try:
        data = json.loads(hits[0].read_text(encoding="utf-8"))
        correct = data.get("correct")
        usage = data.get("token_usage", {})
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        cost = usage.get("estimated_cost_usd", 0.0)
        return correct, inp, out, cost
    except (json.JSONDecodeError, OSError):
        return None, 0, 0, 0.0


def _skip_path(folder_name: str) -> Path:
    return AGENT_DIR / folder_name / "skipped.json"


def _venv_ready(folder_name: str) -> bool:
    """Return True if the per-paper venv already has a Python interpreter.

    A fresh venv means the timeout was likely spent on package installation
    rather than on the actual question — so we should not auto-skip in that case.
    """
    venv = AGENT_DIR / folder_name / ".venv"
    return any(
        (venv / p).exists()
        for p in ("Scripts/python.exe", "bin/python", "bin/python3")
    )


def load_skips(folder_name: str) -> dict:
    """Return the skip registry for a paper, or {} if none exists."""
    p = _skip_path(folder_name)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_skip(folder_name: str, entry_id: str, abort_reason: str) -> None:
    """Record a timed-out question so future runs skip it automatically."""
    skips = load_skips(folder_name)
    skips[entry_id] = {
        "abort_reason": abort_reason,
        "skipped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    p = _skip_path(folder_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(skips, indent=2), encoding="utf-8")


def run_question(
    slug: str,
    entry: dict,
    biorxiv_url: str,
    model: str | None,
    team: str | None,
    timeout: int | None = 120,
) -> tuple[int, bool]:
    """Call react_main for a single question. Returns (exit_code, timed_out).

    Pass timeout=None to run with no time limit (used when the venv is being
    created for the first time, so installation time does not count against
    the question budget).
    """
    cmd = [
        "uv", "run", "python", "-m", "research_agents.react_main",
        "--project", f"papers/{slug}",
        "--question", entry["question"],
        "--id", entry["id"],
        "--ground-truth", entry.get("ground_truth", ""),
        "--biorxiv-url", biorxiv_url,
    ]
    if model:
        cmd += ["--model", model]
    if team:
        cmd += ["--team", team]
    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(cmd, cwd=ROOT, env=child_env)
    try:
        proc.wait(timeout=timeout)
        return proc.returncode, False
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return -1, True


def fmt_duration(seconds: float) -> str:
    """Format a duration in seconds as Xh Ym Zs, omitting leading zeros."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def print_session_total(
    done: int,
    total: int,
    correct: int,
    session_input: int,
    session_output: int,
    session_cost: float,
    session_start: float,
) -> None:
    """Print the running session accumulator after each question."""
    bar_width = 30
    filled = int(bar_width * done / total) if total else bar_width
    bar = "█" * filled + "░" * (bar_width - filled)

    elapsed = time.time() - session_start
    avg_per_q = elapsed / done
    remaining = avg_per_q * (total - done)
    acc = correct / done * 100

    print(f"\n  [{bar}] {done}/{total} questions")
    print(f"  Accuracy       : {correct}/{done}  ({acc:.1f}%)")
    print(f"  Elapsed        : {fmt_duration(elapsed)}  |  "
          f"ETA {fmt_duration(remaining)}  (~{fmt_duration(avg_per_q)}/question)")
    print(f"  Session tokens : {session_input + session_output:>12,}  "
          f"(in {session_input:,} / out {session_output:,})")
    print(f"  Session cost   : ${session_cost:>10.4f}")


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch eval runner — resolves repo ranks to questions and runs the agent."
    )
    parser.add_argument(
        "--repos", nargs="+", required=True,
        help="Rank numbers or ranges, e.g. --repos 1-21  or  --repos 1 3 7",
    )
    parser.add_argument(
        "--model", default=None,
        help="Model override passed to react_main",
    )
    parser.add_argument(
        "--team", default=None,
        help="Team override passed to react_main (e.g. worker-critic-plus)",
    )
    parser.add_argument(
        "--questions", nargs="+", default=None, metavar="N",
        help=(
            "1-based question indices (or ranges) to run within each repo, "
            "e.g. --questions 3  or  --questions 1 3  or  --questions 2-4. "
            "Omit to run all questions."
        ),
    )
    parser.add_argument(
        "--timeout", type=int, default=120, metavar="SECONDS",
        help=(
            "Per-question wall-clock time limit in seconds. "
            "Questions that exceed this are killed and automatically "
            "skipped in future runs. Default: 120 (2 min)."
        ),
    )
    parser.add_argument(
        "--ignore-skips", action="store_true",
        help="Run all questions even if previously marked as timed out.",
    )
    args = parser.parse_args()

    question_indices: set[int] | None = (
        set(parse_ranks(args.questions)) if args.questions else None
    )

    print(f"[config] Per-question timeout: {args.timeout}s "
          f"({args.timeout // 60}m {args.timeout % 60}s)")

    ranks = parse_ranks(args.repos)
    print(f"Ranks to run: {ranks}\n")

    # ── Pre-flight: resolve all repos and count total questions ────────────
    plan: list[tuple[int, str, str, Path, list[dict], str]] = []  # (rank, folder_name, id_slug, folder, questions, url)
    skipped: list[str] = []

    for rank in ranks:
        folder = find_folder(rank)
        if not folder:
            print(f"[{rank:02d}] no Papers/ folder found — skip")
            skipped.append(f"{rank} (no folder)")
            continue

        url = read_biorxiv_url(folder)
        if not url:
            print(f"[{rank:02d}] {folder.name} — missing biorxiv_link.txt — skip")
            skipped.append(f"{rank} (no url)")
            continue

        # folder_name keeps the full tagged name (e.g. "02-5M-GWAS-Epistasis-Bias")
        # so venv, runs, and workspace all land inside papers/02-5M-…/ matching
        # the Papers/ layout.  id_slug is the clean name used only for question
        # IDs and the QA JSON file.
        folder_name = folder.name
        id_slug = extract_slug(folder_name)
        questions = load_questions(url, id_slug)

        if question_indices is not None:
            questions = [q for i, q in enumerate(questions, 1) if i in question_indices]

        if not questions:
            print(f"[{rank:02d}] {folder_name} — 0 questions matched ({url}) — skip")
            skipped.append(f"{rank} ({folder_name}, 0 questions)")
            continue

        print(f"[{rank:02d}] {folder_name} — {len(questions)} question(s)")
        plan.append((rank, folder_name, id_slug, folder, questions, url))

    total_questions = sum(len(qs) for _, _, _, _, qs, _ in plan)
    print(f"\nTotal: {len(plan)} repos, {total_questions} questions\n{'='*60}\n")

    # ── Run ────────────────────────────────────────────────────────────────
    session_input   = 0
    session_output  = 0
    session_cost    = 0.0
    session_correct = 0
    done            = 0
    session_start   = time.time()

    for rank, folder_name, id_slug, folder, questions, url in plan:
        setup_workspace(folder_name, folder)
        write_qa_file(id_slug, questions)

        print(f"\n{'='*60}")
        print(f"  Repo [{rank:02d}] {folder_name}  —  {len(questions)} question(s)")
        print(f"{'='*60}")

        skips = load_skips(folder_name)

        for i, entry in enumerate(questions, 1):
            print(f"\n  ── Q {i}/{len(questions)} · {entry['id']} ──")
            print(f"  {entry['question'][:100]}{'…' if len(entry['question']) > 100 else ''}")

            # Skip check — bypass if --ignore-skips passed
            if not args.ignore_skips and entry["id"] in skips:
                info = skips[entry["id"]]
                reason = info.get("abort_reason", "unknown")
                when = info.get("skipped_at", "manually")
                print(f"  [SKIP] {reason} (recorded {when}) — skipping.")
                print(f"         Pass --ignore-skips to force a re-run.")
                done += 1
                continue

            # If the venv doesn't exist yet, skip the time limit — the run
            # will spend most of its time on package installation, not the
            # actual question, so killing it early would be wrong.
            effective_timeout = args.timeout if _venv_ready(folder_name) else None
            if effective_timeout is None:
                print(f"  [no timeout] venv not ready yet — running without time limit")

            q_start = time.time()
            rc, timed_out = run_question(folder_name, entry, url, args.model, args.team, effective_timeout)
            q_duration = time.time() - q_start

            if rc != 0 and not timed_out:
                print(f"  [WARN] react_main exited {rc} for {entry['id']}")

            correct, inp, out, cost = read_latest_result(folder_name, entry["id"])
            session_input   += inp
            session_output  += out
            session_cost    += cost
            if correct:
                session_correct += 1
            done += 1

            if timed_out:
                save_skip(folder_name, entry["id"], "time_limit")
                skips[entry["id"]] = {"abort_reason": "time_limit"}
                print(f"  [TIMEOUT] {entry['id']} killed after {args.timeout}s — added to skipped.json.")

            verdict = "✓ correct" if correct else ("✗ wrong" if correct is False else "? unknown")
            if timed_out:
                verdict = "⚠ timed out"
            print(f"\n  This question  : {verdict}  |  took {fmt_duration(q_duration)}  |  in={inp:,}  out={out:,}  ${cost:.4f}")
            print_session_total(done, total_questions, session_correct, session_input, session_output, session_cost, session_start)

    # ── Final summary ──────────────────────────────────────────────────────
    elapsed = time.time() - session_start
    print(f"\n{'='*60}")
    print("DONE")
    print(f"  Repos run      : {len(plan)}")
    print(f"  Questions run  : {done}/{total_questions}")
    print(f"  Accuracy       : {session_correct}/{done}  ({session_correct/done*100:.1f}%)" if done else "  Accuracy       : n/a")
    print(f"  Total time     : {fmt_duration(elapsed)}")
    print(f"  Total tokens   : {session_input + session_output:,}  "
          f"(in {session_input:,} / out {session_output:,})")
    print(f"  Total cost     : ${session_cost:.4f}")
    if skipped:
        print(f"  Skipped        : {skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
