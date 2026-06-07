# RQ3 README-assist — second pair (solo + HITL-autonomous): results & summary

Mirror of the first README experiment, for the two remaining agents. A shared set of 18
per-paper READMEs of steering tips — distilled from **solo + HITL's own** autonomous failures
— was injected at run time; all 46 questions were re-run per team and compared to the
autonomous baselines.

## Headline results (hand-audited; corrects scorer false-neg/pos)

| Team | Autonomous baseline | + Help README | Δ |
|---|---|---|---|
| **solo** | 17 / 46 effective-correct | **28 / 46** | **+11** |
| **human-in-the-loop (autonomous)** | 21–23 / 46 effective-correct | **~32 / 46** | **~+10** |

- solo: **~13 recovered, 2 regressed.** Cost $4.74. help_provided 46/46.
- HITL: **~15 recovered, ~3 regressed.** Cost ~$9. help_provided 46/46. (SCISTREECNA_003 is a
  confirmed regression — it blocked on re-run; the scistreecna inference couldn't be reproduced here.)
- Scorer-only tally was solo 25 / HITL 29; the audited numbers add TabPFN ×2 per team (correct
  metrics the scorer can't parse) and the CROSSPPI_001 near-miss. ARCADIA_003 flips 162→6 (a real
  recovery the baseline scorer had hidden as a false-positive).

## What the help recovered (by theme)
- **Give-up prevention (solo's biggest weakness):** SEGMA (ran on CPU instead of giving up),
  GWAS_001/002/003, LARIS_002, DISTORTIONS_005, METAPOINT_004, TabPFN ×2, CROSSPPI_001/003 — solo
  had abandoned these (no install-retry / claimed GPU / claimed license). The "install deps
  yourself / runs on CPU / weights are cached" tips fixed them.
- **SAM2 mode bug (both teams, the new tip):** HITL baseline produced **3** masks (single-prompt);
  with "use the AUTOMATIC mask generator with defaults" it produced **52 / 54** (real, grounded).
- **Conceptual fixes carried over:** CROSSPPI_006 (strip ESM BOS/EOS → 216), PPLM_001 (affinity
  script + numpy<2 → -8.2265625), ARCADIA_003 (grid-count → 6), CyteOnto, RegFormer, FADVI, GWProt.

## Regressions (the cost)
- **solo METAPOINT_001 (1182→312) / METAPOINT_002 (37→38):** different counting under the staged
  inputs — the metapoint tip nudged a different interpretation.
- **HITL REGFORMER_003 (512→blocked):** tried to regenerate embeddings via the pipeline and the
  data wasn't reproducible here.
- **HITL SCISTREECNA_003 (was correct → blocked):** confirmed regression — the scistreecna
  inference couldn't be reproduced here on re-run (baseline had gotten it via 11 executions).
- **HITL CYTEONTO_001:** the integrity guard downgraded a derived-but-ungrounded "4" (baseline
  counted it correct); a guard artifact, not a wrong answer.

## Cross-experiment picture (all four agents)
The README helps **every** agent, and most where the agent was weakest:

| Agent | Baseline → README |
|---|---|
| worker-critic | 24 → 33 (+9) |
| worker-critic-plus-plus | 26 → 36 (+10) |
| solo | 17 → 28 (+11) |
| human-in-the-loop | 21–23 → ~32 (~+10) |

## Integrity
Every ground-truth value was grepped against the (new) READMEs: clean — the only matches are the
char `6` inside "162" (the cited wrong answer) and `0` inside "exit code 0". Key recoveries were
confirmed grounded in real execution (SAM2 mask generation, PPLM affinity run, SEGMA, FADVI).
No answer was planted; the gains are method-driven.

## Where everything is
- READMEs: `help/<slug>.md`. Runs: `solo-readme/`, `human-in-the-loop-readme/` (chains/logs/traces/
  costs/manifest, with `help_provided`). Analysis: `analysis/comparison.md`, this file. Baselines:
  `experiments-full-runs/{solo-batch, human-in-the-loop-batch}/`. Code: `solo_readme.py`,
  `human_in_the_loop_readme.py` (HITL crew unchanged — help injected only). 241 tests pass.
