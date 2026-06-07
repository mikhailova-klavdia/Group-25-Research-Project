#!/usr/bin/env python
"""Autonomous sweep runner for the README-assisted teams (RQ3 static-help).

Runs all 46 questions for one README-assisted team. Before running, it places each paper's
help file (``help/<slug>.md``) at ``papers/<slug>/AGENT_HINTS.md`` — alongside the repo —
so the team's ``read_help`` tool and the injected TASK HINTS preamble pick it up.

There is NO human in the loop here (the help is static), so this runs fully unattended with
the SAME settings as the autonomous baselines — one question at a time, fresh venv wiped
before AND after each question (weights live outside it), max-turns 50, a 600s wall-clock
cap, ``--trace`` — making the help README the only variable vs the baseline. Saves chain +
log + trace + costs + a manifest row. RESUMABLE: a question whose chain already exists is
skipped. Stale-output guard: a chain/trace is accepted only if written during this run
(``mtime >= t0``) AND its ``team`` field matches.

Usage:  uv run python <evaldir>/run_readme_sweep.py <team> [--limit N]
  team ∈ {worker-critic-readme, worker-critic-plus-plus-readme}
"""
import csv
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parent
ROOT = EVAL.parents[1]
QDIR = EVAL / "questions"
HELPDIR = EVAL / "help"
MODEL = "gpt-5-mini-2025-08-07"
MAX_TURNS = "50"
# The help legitimately directs MORE work than the give-up-prone baselines (dependency
# installs, running pipelines, generating inputs), so a 600s cap killed the heavy questions
# mid-work. A question that finished under 600s is unaffected by a higher cap, so raising it
# only lets the slow-but-progressing ones complete. Recorded in the summary as a deliberate
# difference from the baseline's 600s.
TIMEOUT_S = 1800


def place_help_files() -> int:
    """Copy each paper's help/<slug>.md to papers/<slug>/AGENT_HINTS.md (alongside the repo)."""
    n = 0
    for hf in HELPDIR.glob("*.md"):
        slug = hf.stem
        proj = ROOT / "papers" / slug
        if proj.is_dir():
            shutil.copy(hf, proj / "AGENT_HINTS.md")
            n += 1
    return n


def _newest_since(runs: Path, pattern: str, t0: float):
    if not runs.exists():
        return None
    cands = [c for c in runs.glob(pattern) if c.stat().st_mtime >= t0]
    return max(cands, key=lambda x: x.stat().st_mtime) if cands else None


def run_one(team: str, out: Path, slug: str, item: dict) -> tuple:
    pid = item["id"]
    proj = f"papers/{slug}"
    venv = ROOT / proj / ".venv"
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    cmd = [sys.executable, "-u", "-m", "research_agents.react_main",
           "--project", proj, "--question", item["question"],
           "--ground-truth", item.get("ground_truth", ""), "--id", pid,
           "--team", team, "--model", MODEL,
           "--fresh-venv-per-question", "--max-turns", MAX_TURNS, "--trace",
           "--biorxiv-url", item.get("repo_link", "")]

    t0 = time.time()
    status = "ok"
    with open(out / "logs" / f"{pid}.log", "w") as lf:
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
    correct = final = tokens = cost = used_help = ""
    src = _newest_since(runs, f"*/{pid}.json", t0)
    if src:
        try:
            d = json.loads(src.read_text())
        except Exception:
            d = None
        if d is not None and d.get("team") == team:
            shutil.copy(src, out / "chains" / f"{pid}.json")
            correct = d.get("correct")
            final = (d.get("final_answer", "") or "")[:80]
            agg = d.get("token_usage", {}).get("aggregate", {}) or {}
            tokens = agg.get("total_tokens")
            cost = round(agg.get("estimated_cost_usd", 0), 4)
            # Deterministic: was the help README injected into the worker's input?
            used_help = "yes" if d.get("help_provided") else "no"
        else:
            src = None
    if src is None and status == "ok":
        status = "no_chain"

    tr = _newest_since(runs, "*/trace.jsonl", t0)
    if tr:
        shutil.copy(tr, out / "traces" / f"{pid}.jsonl")
    cj = ROOT / proj / "costs.json"
    if cj.exists():
        shutil.copy(cj, out / "costs" / f"{slug}-costs.json")

    fields = ["timestamp", "id", "project", "status", "correct",
              "final_answer", "tokens", "cost_usd", "used_help", "elapsed_s"]
    man = out / "manifest.csv"
    new = not man.exists()
    with open(man, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "id": pid, "project": proj, "status": status, "correct": correct,
            "final_answer": final, "tokens": tokens, "cost_usd": cost,
            "used_help": used_help, "elapsed_s": elapsed,
        })
    return status, correct, cost, used_help, elapsed


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print("usage: run_readme_sweep.py <team> [--limit N]")
        sys.exit(2)
    team = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    out = EVAL / team
    for sub in ("chains", "logs", "costs", "traces"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    placed = place_help_files()
    print(f"[readme-sweep {team}] placed {placed} AGENT_HINTS.md files", flush=True)

    work = []
    for qf in sorted(QDIR.glob("*.json"), key=lambda p: (len(json.loads(p.read_text())), p.stem)):
        for item in json.loads(qf.read_text()):
            work.append((qf.stem, item))
    total = len(work)
    done_marker = out / ".done"
    if done_marker.exists():
        done_marker.unlink()

    print(f"[readme-sweep {team}] {total} questions | model={MODEL} | max-turns={MAX_TURNS}", flush=True)
    ran = 0
    for i, (slug, item) in enumerate(work, 1):
        pid = item["id"]
        if (out / "chains" / f"{pid}.json").exists():
            print(f"[{i}/{total}] SKIP {pid} ({slug}): already done", flush=True)
            continue
        print(f"[{i}/{total}] RUN  {pid} ({slug}) ...", flush=True)
        status, correct, cost, used_help, elapsed = run_one(team, out, slug, item)
        print(f"[{i}/{total}]  -> {status} correct={correct} help={used_help} ${cost} {elapsed}s", flush=True)
        ran += 1
        if limit and ran >= limit:
            print(f"[readme-sweep {team}] hit --limit {limit}; stopping.", flush=True)
            break
    done_marker.write_text("done")
    print(f"[readme-sweep {team}] complete.", flush=True)


if __name__ == "__main__":
    main()
