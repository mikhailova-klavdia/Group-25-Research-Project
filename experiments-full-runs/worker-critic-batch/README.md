# Worker-Critic Batch — Full Run

Full Paper2AgentBench sweep (46 questions) with the `worker-critic` agent team.

- **Date:** 2026-06-04 → 06-05
- **Model:** `gpt-5-mini-2025-08-07` (worker); critic pinned to `gpt-4.1-mini-2025-04-14`
- **Team:** `worker-critic` (ReAct worker + LLM critic + deterministic missing-module install retry; no triage/setup, no integrity guard)
- **Run config:** `--fresh-venv-per-question --max-turns 50 --trace`, unbuffered output, 10-min wall-clock cap per question
- **Questions:** 46 (from `benchmark_42.csv`); each given verbatim, no hints

## How many were correct (manual audit)

Hand-verified against each chain (`AUDIT.md`), past the exact-match scorer — which had both a
false-positive (`ARCADIA_PUBLIC_003`: 162 scored as 6) and false-negatives (`SAM2_001`,
`TABPFN_002` rejected on `~`/fuzzy ground truths).

| Verdict | Count |
|---|---|
| ✓ Solid correct | 17 |
| ≈ Near-miss (effectively right) | 3 |
| ⚠ Value-matches but execution unconfirmed | 4 |
| ✗ Truly wrong | 3 |
| ⊘ Legit blocked (data genuinely absent) | 7 |
| 🛑 Gave up on a *solvable* question | 11 |
| ⏱ No answer (timeout) | 1 |

- **Effectively right: 24 / 46** (17 solid + 3 near + 4 value-matches). Raw scorer said 21.
- **Truly wrong: only 3** — worker-critic rarely commits to a bad answer; it cleanly gives up instead.

See `AUDIT.md` for the per-question verdict + explanation.

## vs the HITL run (audited)

| | worker-critic | HITL |
|---|---:|---:|
| Effectively right | **24** | 23 |
| Truly wrong | **3** | 12 |
| Legit blocked | 7 | 4 |
| Gave up (solvable) | 11 | ~0 |
| Timeouts | **1** | 7 |
| Captured cost | **$5.08** | $8.45 |

Roughly **tied on correct answers**, but opposite error profiles: worker-critic is high-precision /
low-recall (rarely wrong, quits often), HITL is higher-recall / lower-precision (answers more, errs
more, times out more). Worker-critic executed several that HITL got wrong or timed out on
(PPLM_001/004/005, METAPOINT_001, SAM2_001, TABPFN_002).

## Cost (full)

| | Cost | Tokens |
|---|---|---|
| **Captured** (45 answered, full per-question aggregate) | **$5.08** | 18,491,083 |
| Not captured (1 timeout, killed before logging) — *estimated* | ~$0.60 | — |
| **Estimated true total** | **~$5.68** | — |

Per-question cost lives in `chains/<ID>.json` → `token_usage.aggregate`. The `costs/<paper>-costs.json`
files are worker-stage-only and undercount — don't sum those. Authoritative figure = OpenAI dashboard.

## Layout

| Path | What |
|---|---|
| `chains/<ID>.json` | full reasoning chain + tokens/cost per answered question (45) |
| `logs/<ID>.log` | terminal output per question (46) |
| `traces/<ID>.jsonl` | kill-safe per-step trace (46) — present even for the timeout |
| `costs/<paper>-costs.json` | per-paper worker-stage cost log (undercount — see above) |
| `manifest.csv` | one row per question: status, correct, final_answer, tokens, cost, elapsed |
| `sweep_plan.json` | resolved 46-question plan |
| `run_sweep.py` | the runner (resumable; mtime+team stale-guard) |
| `AUDIT.md` | manual per-question correctness audit |
