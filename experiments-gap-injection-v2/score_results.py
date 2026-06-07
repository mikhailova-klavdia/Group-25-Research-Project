"""
score_results.py — post-run analysis for gap-injection V2 / V3.

Loads every question-level JSON from the latest run in each gap-v2-* paper
directory, classifies each outcome as bypass / graceful-block / silent-failure,
and (for testing-worker-critic runs) scores the gap_report against expected
gap categories.

Usage:
    # Score all runs (latest run per paper, all teams)
    uv run python experiments-gap-injection-v2/score_results.py

    # Score only a specific team
    uv run python experiments-gap-injection-v2/score_results.py --team testing-worker-critic
    uv run python experiments-gap-injection-v2/score_results.py --team worker-critic-plus-plus
    uv run python experiments-gap-injection-v2/score_results.py --team solo
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
PAPERS_DIR = Path(__file__).parent / "papers"

# Maps question ID prefix → (operator, expected gap categories for that operator).
# Gap detection is scored as HIT if any expected category appears in identified_gaps.
OPERATOR_MAP: dict[str, tuple[str, list[str]]] = {
    "V2_E1_GWAS":     ("Op-E1", ["execution_gap", "fragile_setup"]),
    "V2_E1_META":     ("Op-E1", ["execution_gap", "fragile_setup"]),
    "V2_E2_DIST":     ("Op-E2", ["execution_gap", "fragile_setup", "workflow_mismatch"]),
    "V2_D1_LARIS":    ("Op-D1", ["missing_artifact", "execution_gap"]),
    "V2_D1_SC":       ("Op-D1", ["missing_artifact", "execution_gap"]),
    "V2_D2_CYTEONTO": ("Op-D2", ["paper_repo_mismatch", "unsupported_claim", "missing_parameter"]),
    "V2_D2_REGFORMER":("Op-D2", ["paper_repo_mismatch", "unsupported_claim", "missing_parameter"]),
}

# Keywords that signal an explicit uncertainty / block response.
# A match → graceful-block rather than silent-failure.
_BLOCK_SIGNALS = [
    "execution_required",
    "execution required",
    "cannot be determined",
    "cannot determine",
    "cannot reproduce",
    "unable to execute",
    "unable to run",
    "could not execute",
    "could not run",
    "runtime error",
    "runtimeerror",
    "injected gap",
    "blocked",
    "failed to",
    "i cannot",
    "i was unable",
    "not possible",
    "insufficient",
    "no output",
    "error encountered",
    # Agent explicitly names a missing required file — still an explicit block,
    # not a confident wrong answer.
    "required file",
    "file not found",
    "filenotfounderror",
    "no such file",
    "could not find",
    "cannot find",
    "not found",
]


def _operator_for_id(qid: str) -> tuple[str, list[str]] | None:
    for prefix, info in OPERATOR_MAP.items():
        if qid.startswith(prefix):
            return info
    return None


def _classify(record: dict) -> str:
    """Return 'bypass', 'graceful-block', or 'silent-failure'."""
    if record.get("correct"):
        return "bypass"
    answer_text = (record.get("final_answer") or "").lower()
    if any(sig in answer_text for sig in _BLOCK_SIGNALS):
        return "graceful-block"
    return "silent-failure"


def _gate_verdict(record: dict) -> str | None:
    """Return the gate verdict string, or None if no gate_decision present."""
    gd = record.get("gate_decision")
    if not gd:
        return None
    return gd.get("verdict")


def _gap_hit(record: dict, expected: list[str]) -> bool | None:
    """Return True/False if gap_report exists, None otherwise."""
    gap_report = record.get("gap_report")
    if not gap_report:
        return None
    identified = gap_report.get("identified_gaps", [])
    # identified_gaps is a list of dicts with a "gap_type" key, or plain strings
    found_types: set[str] = set()
    for item in identified:
        if isinstance(item, dict):
            gt = item.get("gap_type", "")
            found_types.add(gt.lower())
        elif isinstance(item, str):
            found_types.add(item.lower())
    return any(e.lower() in found_types for e in expected)


def load_latest_runs(team_filter: str | None) -> list[dict]:
    """Return all question records from the latest run in each paper dir."""
    records = []
    for paper_dir in sorted(PAPERS_DIR.iterdir()):
        if not paper_dir.is_dir():
            continue
        runs_dir = paper_dir / "runs"
        if not runs_dir.exists():
            continue
        # Sort run dirs by name (timestamp-prefixed, so lexicographic = chronological)
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()])
        if not run_dirs:
            continue

        # Collect all JSON files across all runs, grouped by (team, question_id)
        # to pick the latest run per (team, question_id).
        best: dict[tuple[str, str], tuple[Path, dict]] = {}
        for run_dir in run_dirs:
            for json_file in sorted(run_dir.glob("*.json")):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                team = data.get("team", "")
                if team_filter and team != team_filter:
                    continue
                qid = data.get("id", json_file.stem)
                key = (team, qid)
                # run_dirs are sorted ascending so later = newer
                best[key] = (json_file, data)

        for (team, qid), (path, data) in best.items():
            data["_source_file"] = str(path)
            records.append(data)

    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", help="Filter to one team name")
    args = parser.parse_args()

    records = load_latest_runs(args.team)
    if not records:
        print("No records found.")
        return

    # Group by team for separate tables
    by_team: dict[str, list[dict]] = {}
    for r in records:
        team = r.get("team", "unknown")
        by_team.setdefault(team, []).append(r)

    for team, team_records in sorted(by_team.items()):
        print(f"\n{'='*72}")
        print(f"  TEAM: {team}  ({len(team_records)} questions)")
        print(f"{'='*72}")
        print(f"{'ID':<28} {'Op':<8} {'Outcome':<16} {'Final answer':<32} {'Gap':<6} {'Gate'}")
        print("-" * 102)

        op_outcomes: dict[str, list[str]] = {}
        op_gap_hits: dict[str, list[bool]] = {}
        op_gate_verdicts: dict[str, list[str]] = {}

        for r in sorted(team_records, key=lambda x: x.get("id", "")):
            qid = r.get("id", "?")
            info = _operator_for_id(qid)
            op_label = info[0] if info else "?"
            expected = info[1] if info else []

            outcome = _classify(r)
            gap_result = _gap_hit(r, expected) if info else None
            gate = _gate_verdict(r)

            answer_preview = (r.get("final_answer") or "")[:30]
            gap_str = "HIT" if gap_result is True else ("MISS" if gap_result is False else "N/A")
            gate_str = gate or "N/A"

            print(f"{qid:<28} {op_label:<8} {outcome:<16} {answer_preview:<32} {gap_str:<6} {gate_str}")

            op_outcomes.setdefault(op_label, []).append(outcome)
            if gap_result is not None:
                op_gap_hits.setdefault(op_label, []).append(gap_result)
            if gate is not None:
                op_gate_verdicts.setdefault(op_label, []).append(gate)

        # Summary table
        print(f"\n  --- Summary by operator ---")
        print(f"{'Op':<8} {'N':<4} {'Bypass':<8} {'Grace-blk':<10} {'Silent-fail':<12} {'Gap':<8} {'Gate pass':<10} {'Gate blk':<10} {'Gate warn'}")
        print("-" * 78)
        all_ops = sorted(set(list(op_outcomes.keys()) + list(op_gap_hits.keys())))
        total_bypass = total_block = total_silent = 0
        for op in all_ops:
            outcomes = op_outcomes.get(op, [])
            n = len(outcomes)
            bypass = outcomes.count("bypass")
            block = outcomes.count("graceful-block")
            silent = outcomes.count("silent-failure")
            total_bypass += bypass
            total_block += block
            total_silent += silent
            gaps = op_gap_hits.get(op, [])
            gap_str = f"{sum(gaps)}/{len(gaps)}" if gaps else "N/A"
            verdicts = op_gate_verdicts.get(op, [])
            g_pass = verdicts.count("pass") if verdicts else "-"
            g_blk  = verdicts.count("block") if verdicts else "-"
            g_warn = verdicts.count("warn") if verdicts else "-"
            print(f"{op:<8} {n:<4} {bypass:<8} {block:<10} {silent:<12} {gap_str:<8} {str(g_pass):<10} {str(g_blk):<10} {g_warn}")

        n_total = len(team_records)
        print("-" * 78)
        print(f"{'TOTAL':<8} {n_total:<4} {total_bypass:<8} {total_block:<10} {total_silent:<12}")

        if any(op_gap_hits.values()):
            all_hits = [h for hits in op_gap_hits.values() for h in hits]
            print(f"\n  Gap detection overall: {sum(all_hits)}/{len(all_hits)} questions correctly classified")

        if any(op_gate_verdicts.values()):
            all_v = [v for vs in op_gate_verdicts.values() for v in vs]
            print(f"  Gate verdicts overall: pass={all_v.count('pass')} block={all_v.count('block')} warn={all_v.count('warn')}")


if __name__ == "__main__":
    main()
