#!/usr/bin/env python
"""Parallel-by-paper sweep runner for the SOLO benchmark (benchmark_42.csv, 46 Qs).

Runs PAPERS in parallel (K workers) but each paper's questions SEQUENTIALLY, so the shared
papers/<slug>/.venv is never touched concurrently. Different papers have different venv
paths / runs dirs / cost logs, so cross-paper parallelism is collision-free. The only shared
resource — the eval-dir manifest.csv — is guarded by a lock.

Per-question behavior is identical to the sequential runs: fresh venv wiped before AND after
(weights persist outside it), 10-min cap, --trace (kill-safe), unbuffered output. Saves
chains/<ID>.json, logs/<ID>.log, traces/<ID>.jsonl, costs/<paper>-costs.json, manifest.csv.
RESUMABLE (skips questions whose chain already exists). Stale-guard: a chain/trace is accepted
only if written DURING this run (mtime >= t0) AND its team field matches.

Config: team=solo, model=gpt-5-mini, --fresh-venv-per-question, --max-turns 50, K=3 papers.

Usage:
  uv run python eval_runs/<dir>/run_sweep.py [--workers K] [--limit-papers N]
"""
import concurrent.futures
import csv
import difflib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parent
ROOT = EVAL.parents[1]
CSV_PATH = ROOT / "benchmark_42.csv"
MODEL = "gpt-5-mini-2025-08-07"
TEAM = "solo"
MAX_TURNS = "50"
TIMEOUT_S = 600
WORKERS = 3                               # papers running in parallel
CHAINS, LOGS, COSTS, TRACES = EVAL / "chains", EVAL / "logs", EVAL / "costs", EVAL / "traces"
MANIFEST = EVAL / "manifest.csv"
PLAN_JSON = EVAL / "sweep_plan.json"
for d in (CHAINS, LOGS, COSTS, TRACES):
    d.mkdir(exist_ok=True)

_manifest_lock = threading.Lock()
_io_lock = threading.Lock()


def _log(msg: str) -> None:
    with _io_lock:
        print(msg, flush=True)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _build_plan() -> list[dict]:
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
            "id": pid, "repo": repo,
            "project": f"papers/{proj}" if proj else None,
            "question": q, "ground_truth": str(r["ground_truth"]),
            "biorxiv": r.get("biorxiv_link", ""),
        })
    PLAN_JSON.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    return plan


def _append_manifest(row: dict) -> None:
    fields = ["timestamp", "id", "project", "status", "correct",
              "final_answer", "tokens", "cost_usd", "elapsed_s"]
    with _manifest_lock:
        new = not MANIFEST.exists()
        with open(MANIFEST, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if new:
                w.writeheader()
            w.writerow(row)


def _newest_since(runs: Path, pattern: str, t0: float):
    if not runs.exists():
        return None
    cands = [c for c in runs.glob(pattern) if c.stat().st_mtime >= t0]
    return max(cands, key=lambda x: x.stat().st_mtime) if cands else None


def _run_one(item: dict) -> tuple:
    pid, proj = item["id"], item["project"]
    venv = ROOT / proj / ".venv"
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    cmd = [sys.executable, "-u", "-m", "research_agents.react_main",
           "--project", proj, "--question", item["question"],
           "--ground-truth", item["ground_truth"], "--id", pid,
           "--team", TEAM, "--model", MODEL,
           "--fresh-venv-per-question", "--max-turns", MAX_TURNS, "--trace",
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

    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    runs = ROOT / proj / "runs"
    correct = final = tokens = cost = ""
    src = _newest_since(runs, f"*/{pid}.json", t0)
    if src:
        try:
            d = json.loads(src.read_text())
        except Exception:
            d = None
        if d is not None and d.get("team") == TEAM:
            shutil.copy(src, CHAINS / f"{pid}.json")
            correct = d.get("correct")
            final = (d.get("final_answer", "") or "")[:80]
            agg = d.get("token_usage", {}).get("aggregate", {}) or {}
            tokens = agg.get("total_tokens")
            cost = round(agg.get("estimated_cost_usd", 0), 4)
        else:
            src = None
    if src is None and status == "ok":
        status = "no_chain"

    tr = _newest_since(runs, "*/trace.jsonl", t0)
    if tr:
        shutil.copy(tr, TRACES / f"{pid}.jsonl")

    cj = ROOT / proj / "costs.json"
    if cj.exists():
        shutil.copy(cj, COSTS / f"{Path(proj).name}-costs.json")

    _append_manifest({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "id": pid, "project": proj, "status": status, "correct": correct,
        "final_answer": final, "tokens": tokens, "cost_usd": cost, "elapsed_s": elapsed,
    })
    return status, correct, cost, elapsed


def _run_paper(project: str, items: list[dict]) -> None:
    """Run ALL questions for one paper, strictly sequentially (shared venv path)."""
    for item in items:
        pid = item["id"]
        if (CHAINS / f"{pid}.json").exists():
            _log(f"  SKIP {pid}  (already done)")
            continue
        _log(f"  RUN  {pid}  ({project}) ...")
        status, correct, cost, elapsed = _run_one(item)
        _log(f"  DONE {pid}: {status} correct={correct} ${cost} {elapsed}s")


def main() -> None:
    workers = WORKERS
    limit_papers = None
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
    if "--limit-papers" in sys.argv:
        limit_papers = int(sys.argv[sys.argv.index("--limit-papers") + 1])

    plan = _build_plan()
    by_paper: "OrderedDict[str, list]" = OrderedDict()
    for item in plan:
        if item["project"] is None:
            continue
        by_paper.setdefault(item["project"], []).append(item)
    papers = list(by_paper.items())
    if limit_papers:
        papers = papers[:limit_papers]

    nq = sum(len(v) for _, v in papers)
    _log(f"[sweep] solo | {nq} questions across {len(papers)} papers | {workers} papers in parallel")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_run_paper, proj, items): proj for proj, items in papers}
        for fut in concurrent.futures.as_completed(futs):
            proj = futs[fut]
            try:
                fut.result()
                _log(f"[paper complete] {proj}")
            except Exception as e:
                _log(f"[paper ERROR] {proj}: {e}")
    _log("[sweep] complete.")


if __name__ == "__main__":
    main()
