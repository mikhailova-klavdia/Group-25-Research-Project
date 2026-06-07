#!/usr/bin/env python
"""Compare the README-assisted re-runs against the autonomous baselines, per team.

For each team it tallies the re-run (scorer-correct / blocked / answered-wrong), then aligns
each re-run question to its autonomous baseline and reports FLIPS:
  - recovered: baseline wrong/blocked  -> re-run scorer-correct
  - regressed: baseline correct        -> re-run wrong/blocked

ID alignment:
  - worker-critic: baseline uses the same canonical IDs -> match by ID.
  - worker-critic-plus-plus: baseline used different per-paper numbering -> match by
    (paper, ground_truth), which is unique within a paper.

Writes analysis/comparison.md. Scorer correctness is objective but imperfect (the known
false-neg/pos are flagged in AUDIT.md); the flips listed here are the spot-check shortlist.
"""
import json, glob, re, os, collections

BASE = "eval_runs/2026-06-07-rq3-readme-assist-solo-hitl"
RERUN = {
    "solo": f"{BASE}/solo-readme/chains",
    "human-in-the-loop": f"{BASE}/human-in-the-loop-readme/chains",
}
BASELINE = {
    "solo": "experiments-full-runs/solo-batch/chains",
    "human-in-the-loop": "experiments-full-runs/human-in-the-loop-batch/chains",
}


def paper_of(cid):
    p = re.sub(r"_\d+$", "", cid).upper()
    return {"METAPOINTFINDER": "METAPOINT"}.get(p, p)


def load(dirp):
    out = {}
    for f in glob.glob(f"{dirp}/*.json"):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        out[d.get("id") or os.path.basename(f)[:-5]] = d
    return out


def status_of(d):
    if d is None:
        return "MISSING"
    if d.get("correct") is True:
        return "correct"
    fa = (d.get("failure_analysis") or {}).get("answer_status", "")
    if fa == "blocked" or "EXECUTION_REQUIRED" in (d.get("final_answer", "") or ""):
        return "blocked"
    return "wrong"


def main():
    lines = ["# README-assisted vs autonomous baseline\n"]
    for team in RERUN:
        rerun = load(RERUN[team])
        base = load(BASELINE[team])
        # index baseline by (paper, gt) for cross-ID matching
        base_by_gt = {}
        for cid, d in base.items():
            base_by_gt[(paper_of(cid), (d.get("ground_truth", "") or "").strip())] = d

        n = len(rerun)
        tally = collections.Counter(status_of(d) for d in rerun.values())
        recovered, regressed = [], []
        for cid, d in sorted(rerun.items()):
            # baseline match: same ID first, else (paper, gt)
            b = base.get(cid) or base_by_gt.get((paper_of(cid), (d.get("ground_truth", "") or "").strip()))
            rs, bs = status_of(d), status_of(b)
            if bs in ("wrong", "blocked", "MISSING") and rs == "correct":
                recovered.append((cid, bs, (d.get("final_answer", "") or "")[:50]))
            if bs == "correct" and rs in ("wrong", "blocked"):
                regressed.append((cid, rs, (d.get("final_answer", "") or "")[:50]))

        cost = sum((c.get("token_usage", {}).get("aggregate", {}) or {}).get("estimated_cost_usd", 0)
                   for c in rerun.values())
        help_n = sum(1 for c in rerun.values() if c.get("help_provided"))
        lines += [
            f"\n## {team}",
            f"- re-run questions: {n} | help_provided: {help_n}/{n} | cost ${cost:.2f}",
            f"- scorer tally: correct={tally['correct']} wrong={tally['wrong']} blocked={tally['blocked']} missing={tally['MISSING']}",
            f"- **recovered (baseline wrong/blocked -> re-run correct): {len(recovered)}**",
        ]
        for cid, bs, fin in recovered:
            lines.append(f"    + {cid}: was {bs} -> now correct ({fin})")
        lines.append(f"- **regressed (baseline correct -> re-run wrong/blocked): {len(regressed)}**")
        for cid, rs, fin in regressed:
            lines.append(f"    - {cid}: was correct -> now {rs} ({fin})")
    out = f"{BASE}/analysis/comparison.md"
    open(out, "w").write("\n".join(lines))
    print("wrote", out)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
