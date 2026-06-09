#!/usr/bin/env python
"""Sequential local sweep runner for the HITL benchmark (benchmark_42.csv, 46 Qs).

Runs each question ONE AT A TIME in a FRESH venv (wiped before each run), capped at
10 minutes, saving the full chain + terminal log + costs into this eval dir, and
appending a row to manifest.csv. RESUMABLE: skips any question whose chain JSON
already exists (so CYTEONTO_001, already done, is skipped; an interrupted sweep
resumes where it left off).

The agent gets NO hints: the verbatim CSV question is passed through; correctness is
only read back afterwards from the saved chain. Config matches the first run:
team=human-in-the-loop, model=gpt-5-mini, --fresh-venv-per-question, --max-turns 50.

Usage:
  uv run python eval_runs/<dir>/run_sweep.py [--limit N]   # N = run at most N undone Qs
"""
import csv
import difflib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parent
ROOT = EVAL.parents[1]                       # repo root
CSV_PATH = ROOT / "benchmark_42.csv"
MODEL = "gpt-5-mini-2025-08-07"
TEAM = "human-in-the-loop"
MAX_TURNS = "50"
TIMEOUT_S = 600                              # 10-minute wall-clock cap per question
CHAINS, LOGS, COSTS = EVAL / "chains", EVAL / "logs", EVAL / "costs"
MANIFEST = EVAL / "manifest.csv"
PLAN_JSON = EVAL / "sweep_plan.json"
for d in (CHAINS, LOGS, COSTS):
    d.mkdir(exist_ok=True)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _build_plan() -> list[dict]:
    """Resolve every CSV row to (id, project, question, ground_truth, biorxiv).

    IDs come from an exact/fuzzy match against question-answers/*.json (so they line
    up with the team's canonical numbering); rows with no match get a
    canonical-prefix fallback id.  Deterministic, so re-running reproduces the plan.
    """
    qa: dict[str, str] = {}
    for f in sorted((ROOT / "question-answers").glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        for e in data:
            if isinstance(e, dict) and e.get("question") and e.get("id"):
                qa[norm(e["question"])] = e["id"]
    qa_keys = list(qa.keys())
    papers = {p.name.lower(): p.name for p in (ROOT / "papers").iterdir() if p.is_dir()}

    counters: dict[str, int] = {}
    plan = []
    for r in csv.DictReader(open(CSV_PATH)):
        repo, q = r["repo"], r["question"]
        n = norm(q)
        if n in qa:
            pid = qa[n]
        else:
            close = difflib.get_close_matches(n, qa_keys, n=1, cutoff=0.9)
            if close:
                pid = qa[close[0]]
            else:
                prefix = repo.upper().replace("-", "_")
                counters[prefix] = counters.get(prefix, 0) + 1
                pid = f"{prefix}_{counters[prefix]:03d}"
        proj = papers.get(repo.lower())
        plan.append({
            "id": pid,
            "repo": repo,
            "project": f"papers/{proj}" if proj else None,
            "question": q,
            "ground_truth": str(r["ground_truth"]),
            "biorxiv": r.get("biorxiv_link", ""),
        })
    PLAN_JSON.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    return plan


def _append_manifest(row: dict) -> None:
    fields = ["timestamp", "id", "project", "status", "correct",
              "final_answer", "tokens", "cost_usd", "elapsed_s"]
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)


def _run_one(item: dict) -> tuple:
    pid, proj = item["id"], item["project"]
    venv = ROOT / proj / ".venv"
    # Ensure the venv is GONE before the run (belt-and-suspenders; --fresh-venv also does this).
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    cmd = [sys.executable, "-m", "research_agents.react_main",
           "--project", proj, "--question", item["question"],
           "--ground-truth", item["ground_truth"], "--id", pid,
           "--team", TEAM, "--model", MODEL,
           "--fresh-venv-per-question", "--max-turns", MAX_TURNS,
           "--biorxiv-url", item["biorxiv"]]

    t0 = time.time()
    status = "ok"
    with open(LOGS / f"{pid}.log", "w") as lf:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT,
                             start_new_session=True)
        try:
            p.communicate(timeout=TIMEOUT_S)
            if p.returncode != 0:
                status = f"exit_{p.returncode}"
        except subprocess.TimeoutExpired:
            status = "timeout"
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:
                pass
            p.wait()
    elapsed = round(time.time() - t0, 1)

    # Clean the venv AFTER too (a killed run won't have hit react_main's own cleanup).
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    correct = final = tokens = cost = ""
    runs = ROOT / proj / "runs"
    src = None
    if runs.exists():
        # Only accept a chain written DURING this question's run (mtime >= t0).
        # Otherwise a timed-out/errored run (which never saved a fresh chain)
        # would grab a stale <id>.json left in runs/ by an earlier sweep of the
        # same paper — silently recording someone else's old answer.
        cands = [c for c in runs.glob(f"*/{pid}.json") if c.stat().st_mtime >= t0]
        if cands:
            src = max(cands, key=lambda x: x.stat().st_mtime)
    if src:
        shutil.copy(src, CHAINS / f"{pid}.json")
        try:
            d = json.loads(src.read_text())
            correct = d.get("correct")
            final = (d.get("final_answer", "") or "")[:80]
            agg = d.get("token_usage", {}).get("aggregate", {})
            tokens = agg.get("total_tokens")
            cost = round(agg.get("estimated_cost_usd", 0), 4)
        except Exception:
            pass
    elif status == "ok":
        status = "no_chain"

    cj = ROOT / proj / "costs.json"
    if cj.exists():
        shutil.copy(cj, COSTS / f"{Path(proj).name}-costs.json")

    _append_manifest({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "id": pid, "project": proj, "status": status, "correct": correct,
        "final_answer": final, "tokens": tokens, "cost_usd": cost, "elapsed_s": elapsed,
    })
    return status, correct, cost, elapsed


def main() -> None:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    plan = _build_plan()
    total = len(plan)
    print(f"[sweep] plan has {total} questions; chains dir = {CHAINS}", flush=True)
    done = 0
    for i, item in enumerate(plan, 1):
        pid = item["id"]
        if item["project"] is None:
            print(f"[{i}/{total}] SKIP {pid}: no project dir", flush=True)
            continue
        if (CHAINS / f"{pid}.json").exists():
            print(f"[{i}/{total}] SKIP {pid}: already done", flush=True)
            continue
        print(f"[{i}/{total}] RUN  {pid}  ({item['project']}) ...", flush=True)
        status, correct, cost, elapsed = _run_one(item)
        print(f"[{i}/{total}]  -> {status}  correct={correct}  ${cost}  {elapsed}s", flush=True)
        done += 1
        if limit and done >= limit:
            print(f"[sweep] hit --limit {limit}; stopping.", flush=True)
            break
    print("[sweep] complete.", flush=True)


if __name__ == "__main__":
    main()
