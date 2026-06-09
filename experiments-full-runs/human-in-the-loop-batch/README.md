# Human-in-the-Loop Batch — Full Run

Full Paper2AgentBench sweep (46 questions) with the `human-in-the-loop` agent team.

- **Date:** 2026-06-04
- **Model:** `gpt-5-mini-2025-08-07`
- **Team:** `human-in-the-loop` (triage → setup engineer → ReAct worker + integrity critic; run headless/autonomous)
- **Run config:** `--fresh-venv-per-question --max-turns 50`, 10-minute wall-clock cap per question
- **Questions:** 46 (from `benchmark_42.csv`); each given verbatim, no hints

## How many were correct

Two views: the automated exact-match scorer, and a manual audit (`AUDIT.md`) that corrects for
scorer false-positives, integrity-guard downgrades of *correct* answers, near-misses, and external blocks.

Numbers below are after a manual re-verification of every borderline call against the actual chains
(two earlier "near-miss" calls were corrected to wrong, two "correct" downgraded to value-matches-unverified).

| Verdict (manual audit) | Count |
|---|---|
| ✓ True correct (execution-grounded or legit read/count) | 19 |
| ≈ Near-miss (executed, effectively right) | 2 |
| ⚠ Value matches but execution not confirmed (may be coincidental) | 2 |
| ✗ Truly wrong | 12 |
| ⊘ Legit blocked (data/artifacts genuinely absent from repo — not the agent's fault) | 4 |
| ⏱ No answer (timeout / turn-limit) | 7 |

- **Effectively right: 21 / 46** (19 solid + 2 near-miss); **up to 23** if the 2 value-matches-unverified count.
  The automated scorer reported **19**.
- Of the **35** questions where inputs were present and it didn't run out of time/turns: **~21 right, 12 wrong, 2 unverified.**
- Scorer corrections found: `ARCADIA_PUBLIC_003` scored "correct" but is **wrong** (162 vs 6 — "6" is a
  substring of "162"); `CROSSPPI_006` (218 vs 216 — 2 un-stripped ESM-2 special tokens) and
  `GWAS_EPISTASIS_BIAS_003` (its script crashed; 0.80 was a guess) are **wrong**, not near-misses.

→ `AUDIT.md` has the per-question verdict + one-line explanation for all 46. `FINAL_SUMMARY.md` has the raw scorer buckets.

## Cost (full)

| | Cost | Tokens | Wall |
|---|---|---|---|
| **Captured** — 39 answered, full per-question aggregate (all 4 stages) | **$8.45** | 31,093,012 | 137 min |
| **Not captured** — 7 no-answer runs, SIGKILL'd before cost was logged (*estimated*) | ~$4.13 | — | 67 min |
| **Estimated true total** | **~$12.58** | — | ~3.4 h |

- The **$8.45 is the full per-question cost** (triage + setup + worker + critic), summed from each chain's
  `token_usage.aggregate`. It is *not* undercounted.
- The 7 no-answer runs (6 timeouts + 1 turn-limit) made API calls while running but were killed before the
  cost was written, so their cost is absent from the files — estimated here at the same $/min rate.
- **Authoritative billed figure = the OpenAI dashboard.**

> Per-question cost lives in `chains/<ID>.json` → `token_usage.aggregate`.
> The `costs/<paper>-costs.json` files are worker-stage-only and undercount — do **not** sum those.

## Layout

| Path | What |
|---|---|
| `chains/<ID>.json` | full reasoning chain + tokens/cost per answered question (39) |
| `logs/<ID>.log` | terminal output per question (46) |
| `costs/<paper>-costs.json` | per-paper worker-stage cost log (17; undercount — see above) |
| `manifest.csv` | one row per question: status, correct, final_answer, tokens, cost, elapsed |
| `sweep_plan.json` | resolved 46-question plan (id → project → question → ground_truth) |
| `run_sweep.py` | the runner (resumable; skips questions whose chain already exists) |
| `AUDIT.md` | manual per-question correctness audit |
| `FINAL_SUMMARY.md` | automated-scorer buckets |
