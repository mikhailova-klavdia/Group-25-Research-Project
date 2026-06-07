# Worker-Critic-Plus-Plus Batch — Full Run

Full Paper2AgentBench sweep (46 questions) with the `worker-critic-plus-plus` agent team.

- **Date:** 2026-06-01
- **Model:** `gpt-5-mini-2025-08-07`
- **Team:** `worker-critic-plus-plus` (ReAct worker with REACT_INSTRUCTIONS_PLUS_PLUS prompt + LLM critic; same shape as worker-critic-plus with a dedicated prompt variant)
- **Run config:** `--fresh-venv-per-question --max-turns 50`, 10-min wall-clock cap per question
- **Questions:** 46 (from `benchmark_42.csv`); each given verbatim, no hints

## How many were correct

Two views: automated exact-match scorer, and manual audit (`AUDIT.md`) correcting for scorer false-positives.

| Verdict (manual audit) | Count |
|---|---|
| ✓ Correct | 26 |
| ✗ Truly wrong | 7 |
| ⊘ Legit blocked (data/artifacts genuinely absent) | 12 |
| 🛑 Integrity-guard block (solvable but critic rejected) | 1 |

- **Correct: 26 / 46 (56.5%)** after audit; automated scorer reported 27 (one false-positive: ARCADIA_PUBLIC_002 scored "6" as substring of "162").
- **Truly wrong: 7** — agent commits to a wrong answer rather than guessing when unsure.
- Zero timeouts, zero solvable give-ups.

See `AUDIT.md` for the per-question verdict + explanation.

## vs other runs (same 46-question benchmark)

| | **worker-critic-plus-plus** | worker-critic | HITL |
|---|---:|---:|---:|
| Correct (audited) | **26 (56.5%)** | 24 (52.2%) | 23 (50.0%) |
| Truly wrong | 6 | 3 | 12 |
| Legit blocked | **13** | 7 | 4 |
| Gave up (solvable) | **0** | 11 | ~0 |
| Timeouts | **0** | 1 | 7 |
| Captured cost | **$2.27** | $5.08 | $8.45 |
| Est. true total | **~$2.27** | ~$5.68 | ~$12.58 |
| Tokens | **7.7M** | 18.5M | 31M |

Plus-plus is the most accurate of the three runs and by far the cheapest (~2.5x cheaper than worker-critic, ~5.5x cheaper than HITL).

## Cost

| | Cost | Tokens |
|---|---|---|
| **Total (46 questions)** | **$2.27** | 7,668,075 |

Per-question cost lives in `chains/<ID>.json` → `token_usage.estimated_cost_usd`.
The `costs/<paper>-costs.json` files are worker-stage-only and undercount — do **not** sum those.

## Layout

| Path | What |
|---|---|
| `chains/<ID>.json` | full reasoning chain + tokens/cost per question (46) |
| `costs/<paper>-costs.json` | per-paper worker-stage cost log (undercount — see above) |
| `manifest.csv` | one row per question: status, correct, final_answer, tokens, cost, elapsed |
| `AUDIT.md` | manual per-question correctness audit |
