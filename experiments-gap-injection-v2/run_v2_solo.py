"""
run_v2_solo.py — gap-injection v2 experiment runner (solo baseline).

Same 16 questions / 7 repos as run_v2_wc_plus_plus.py, run with the
solo single-agent team for architecture comparison.

Usage:
    uv run python experiments-gap-injection-v2/run_v2_solo.py
    uv run python experiments-gap-injection-v2/run_v2_solo.py --dry-run
    uv run python experiments-gap-injection-v2/run_v2_solo.py --category e1_gwas
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
GAP_DIR = Path(__file__).parent

MODEL = "gpt-5-mini-2025-08-07"
TEAM = "solo"

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

    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.monotonic() - t0
    status = "OK" if result.returncode == 0 else f"EXIT {result.returncode}"
    print(f"\n  [{label}] finished in {elapsed:.0f}s — {status}")


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

    print("\nAll gap-v2 solo runs complete.")


if __name__ == "__main__":
    main()
