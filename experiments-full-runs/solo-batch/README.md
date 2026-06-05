# Solo Batch — Full Run

Full Paper2AgentBench sweep (46 questions) with the `solo` agent team.

- **Date:** 2026-06-05
- **Model:** `gpt-5-mini-2025-08-07`
- **Team:** `solo` (a single ReAct worker — no critic, no install-retry, no triage/setup, no integrity guard)
- **Run config:** `--fresh-venv-per-question --max-turns 50 --trace`, unbuffered output, 10-min cap per question
- **Parallelism:** papers run **3 at a time** (sequential within a paper, so the shared `papers/<slug>/.venv` never collides)
- **Questions:** 46 (from `benchmark_42.csv`); each given verbatim, no hints. Solo's `ground_truth` reaches **no agent at all** (no critic) — only the post-hoc scorer.

## How many were correct (manual audit)

Hand-verified against each chain (`AUDIT.md`), past the exact-match scorer (same false-positive
`ARCADIA_PUBLIC_003`: 162 scored as 6).

| Verdict | Count |
|---|---|
| ✓ Solid correct | 15 |
| ⚠ Value-matches but execution unconfirmed | 2 |
| ✗ Truly wrong | 4 |
| ⊘ Legit blocked (data genuinely absent) | 6 |
| 🛑 Gave up on a *solvable* question | 17 |
| ⏱ No answer (timeout) | 2 |

- **Effectively right: 17 / 46** (15 solid + 2 value-matches). Raw scorer said 18.
- **Truly wrong: 4.** Solo rarely commits to a bad answer — but it **gives up the most** (17 solvable
  questions abandoned), including dependency gaps it cannot self-install (no install-retry: SAM2_001,
  GWAS_002) and questions it wrongly declared blocked (SEGMA_001 "gpu_required", TabPFN "needs license").

See `AUDIT.md` for the per-question verdict + explanation.

## Three-team comparison (all audited)

| | HITL | worker-critic | **solo** |
|---|---:|---:|---:|
| Effectively right | 23 | **24** | 17 |
| Truly wrong | 12 | 3 | 4 |
| Legit blocked | 4 | 7 | 6 |
| Gave up (solvable) | ~0 | 11 | **17** |
| Timeouts | 7 | 1 | 2 |
| Captured cost | $8.45 | $5.08 | **$4.22** |

Clear trend as the team gets simpler (HITL → worker-critic → solo): **fewer wrong answers, far more
give-ups, lower cost.** Worker-critic is the sweet spot (most effectively-right, fewest wrong). Solo is
cheapest and least-wrong-per-answer, but its bareness (no critic, no install-retry) makes it bail so often
that it answers the fewest correctly.

## Cost (full)

| | Cost | Tokens |
|---|---|---|
| **Captured** (44 answered, full per-question aggregate) | **$4.22** | 15,517,280 |
| Not captured (2 timeouts) — *estimated* | ~$1.30 | — |
| **Estimated true total** | **~$5.51** | — |

Per-question cost lives in `chains/<ID>.json` → `token_usage.aggregate`. The `costs/<paper>-costs.json`
files are worker-stage-only and undercount — don't sum those.

## Layout

| Path | What |
|---|---|
| `chains/<ID>.json` | full reasoning chain + tokens/cost per answered question (44) |
| `logs/<ID>.log` | terminal output per question (46) |
| `traces/<ID>.jsonl` | kill-safe per-step trace (46) — present even for timeouts |
| `costs/<paper>-costs.json` | per-paper worker-stage cost log (undercount — see above) |
| `manifest.csv` | one row per question: status, correct, final_answer, tokens, cost, elapsed |
| `sweep_plan.json` | resolved 46-question plan |
| `run_sweep.py` | the **parallel-by-paper** runner (3 papers at once; mtime+team stale-guard, lock-guarded manifest) |
| `AUDIT.md` | manual per-question correctness audit |
