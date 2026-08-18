"""
run_v2_hitl.py — gap-injection v2 experiment runner (human-in-the-loop).

Same 16 questions / 7 repos as run_v2_solo.py and run_v2_wc_plus_plus.py, run
with the human-in-the-loop team (triage -> setup -> execution crew) for
architecture comparison.

This is a headless/batch invocation (react_main, not hitl_main), so any
ask_human calls the setup/execution agents make degrade to autonomous
answers instead of blocking on stdin — see research_agents/teams/__init__.py.

Usage:
    uv run python experiments-gap-injection-v2/run_v2_hitl.py
    uv run python experiments-gap-injection-v2/run_v2_hitl.py --dry-run
    uv run python experiments-gap-injection-v2/run_v2_hitl.py --category e1_gwas

Each question's chain of thought (thought/action/observation/reflection per step) is copied after every category into a flat, browsable location:
    experiments-gap-injection-v2/chains/<TEAM>/<question-id>.json
(react_main still also writes the original to papers/<slug>/runs/<run-id>/ —
this is a convenience copy, not a replacement.)
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
GAP_DIR = Path(__file__).parent

MODEL = "gpt-5-mini-2025-08-07"
TEAM = "human-in-the-loop"

RUNS = [
    (
        "experiments-gap-injection-v2/papers/gap-v2-gwas",
        "experiments-gap-injection-v2/questions/op_e1_gwas.json",
        "Op-E1-GWAS",
    ),
    (
        "experiments-gap-injection-v2/papers/gap-v2-meta",
        "experiments-gap-injection-v2/questions/op_e1_meta.json",
        "Op-E1-META",
    ),
    (
        "experiments-gap-injection-v2/papers/gap-v2-distortions",
        "experiments-gap-injection-v2/questions/op_e2_distortions.json",
        "Op-E2-DISTORTIONS",
    ),
    (
        "experiments-gap-injection-v2/papers/gap-v2-laris",
        "experiments-gap-injection-v2/questions/op_d1_laris.json",
        "Op-D1-LARIS",
    ),
    (
        "experiments-gap-injection-v2/papers/gap-v2-sc-framework",
        "experiments-gap-injection-v2/questions/op_d1_sc_framework.json",
        "Op-D1-SC-FRAMEWORK",
    ),
    (
        "experiments-gap-injection-v2/papers/gap-v2-cyteonto",
        "experiments-gap-injection-v2/questions/op_d2_cyteonto.json",
        "Op-D2-CYTEONTO",
    ),
    (
        "experiments-gap-injection-v2/papers/gap-v2-regformer",
        "experiments-gap-injection-v2/questions/op_d2_regformer.json",
        "Op-D2-REGFORMER",
    ),
]


def _newest_since(runs_dir: Path, pattern: str, t0: float):
    """Newest file under runs_dir matching pattern, written at/after t0 (wall-clock)."""
    if not runs_dir.exists():
        return None
    cands = [c for c in runs_dir.glob(pattern) if c.stat().st_mtime >= t0]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def save_chains(project: str, questions_file: str, label: str, t0: float) -> None:
    """Copy each question's chain JSON out of the scattered per-question
    runs/<run-id>/<id>.json (react_main's default location, one fresh run-id
    per question even in batch mode) into a single flat, easy-to-browse
    experiments-gap-injection-v2/chains/<TEAM>/<id>.json — mirroring the
    <run>/<team>/chains/*.json layout already used under eval_runs/.
    """
    entries = json.loads((ROOT / questions_file).read_text(encoding="utf-8"))
    runs_dir = ROOT / project / "runs"
    out_dir = GAP_DIR / "chains" / TEAM
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        qid = entry["id"]
        src = _newest_since(runs_dir, f"*/{qid}.json", t0)
        if src is None:
            print(f"  [chains] WARNING: no chain file found for {qid} ({label}) — check the log above")
            continue
        dest = out_dir / f"{qid}.json"
        shutil.copy(src, dest)
        print(f"  [chains] saved {dest.relative_to(ROOT)}")


def run_category(project: str, questions_file: str, label: str, dry_run: bool) -> None:
    cmd = [
        sys.executable, "-m", "research_agents.react_main",
        "--project", str(ROOT / project),
        "--questions-file", str(ROOT / questions_file),
        "--team", TEAM,
        "--model", MODEL,
        "--isolated",
    ]

    print(f"\n{'='*60}")
    print(f"  {label}  [{TEAM}]")
    print(f"  project  : {project}")
    print(f"  questions: {questions_file}")
    print(f"{'='*60}")

    if dry_run:
        print(f"  [dry-run] would run: {' '.join(cmd)}")
        return

    t0_wall = time.time()
    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.monotonic() - t0
    status = "OK" if result.returncode == 0 else f"EXIT {result.returncode}"
    print(f"\n  [{label}] finished in {elapsed:.0f}s — {status}")

    save_chains(project, questions_file, label, t0_wall)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--category",
        choices=["e1_gwas", "e1_meta", "e2_distortions", "d1_laris", "d1_sc", "d2_cyteonto", "d2_regformer"],
        help="Run only one category; omit to run all",
    )
    args = parser.parse_args()

    label_map = {
        "e1_gwas":        "Op-E1-GWAS",
        "e1_meta":        "Op-E1-META",
        "e2_distortions": "Op-E2-DISTORTIONS",
        "d1_laris":       "Op-D1-LARIS",
        "d1_sc":          "Op-D1-SC-FRAMEWORK",
        "d2_cyteonto":    "Op-D2-CYTEONTO",
        "d2_regformer":   "Op-D2-REGFORMER",
    }

    targets = RUNS
    if args.category:
        target_label = label_map[args.category]
        targets = [r for r in RUNS if r[2] == target_label]

    for project, questions_file, label in targets:
        run_category(project, questions_file, label, args.dry_run)

    print("\nAll gap-v2 human-in-the-loop runs complete.")


if __name__ == "__main__":
    main()
