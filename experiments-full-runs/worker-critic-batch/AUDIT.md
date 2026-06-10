# Worker-Critic — per-question correctness audit (verified vs chains)

gpt-5-mini · worker-critic · 46 questions.

## True tally

| Verdict | Count |
|---|---|
| ✓ TRUE CORRECT | 17 |
| ≈ NEAR-MISS | 3 |
| ⚠ VALUE-MATCHES (unconfirmed) | 4 |
| ✗ TRULY WRONG | 3 |
| ⊘ LEGIT BLOCKED (external) | 7 |
| 🛑 GAVE UP (solvable — HITL/pre-DL had it) | 11 |
| ⏱ NO ANSWER (timeout) | 1 |

**Effectively right: 24/46** (17 solid + 3 near + 4 value-matches) · truly wrong: 3


## ✓ TRUE CORRECT (17)
- **CYTEONTO_002** — stem cell = truth (read from notebook; no guard, so it stands).
- **CYTEONTO_003** — ovum = truth.
- **GWAS_EPISTASIS_BIAS_001** — executed; 5.0369820e-08 = truth.
- **SENTIEON_CLI_001** — CONSERVATIVE = truth.
- **GWPROT_001** — counted 54 PDBs = truth.
- **GWPROT_002** — 4 = truth (HITL guard-downgraded this; here it stands).
- **SC_FRAMEWORK_001** — executed; 5000 = truth.
- **REGFORMER_002** — 0.8841 = truth.
- **PPLM_001** — executed; -8.2265625 = truth. (HITL got this WRONG: -10.66.)
- **PPLM_002** — 3 execs; favorable = truth.
- **PPLM_003** — 4 execs; (122,1280) = truth.
- **PPLM_004** — 5 execs; -0.000396 = truth. (HITL TIMED OUT here.)
- **PPLM_005** — 4 execs; (660,122,70) = truth — execution-grounded (HITL's was unverified).
- **PPLM_006** — 3 execs; 0.9431081 ~ truth.
- **METAPOINT_001** — 2 execs; 1182 = truth. (HITL TIMED OUT here.)
- **METAPOINT_002** — 2 execs; 37 = truth.
- **SAM2_001** — executed; 52 masks = ~52 truth. SCORER FALSE NEGATIVE (rejected the '~'). (HITL got 3 — wrong.)

## ≈ NEAR-MISS (3)
- **GWAS_EPISTASIS_BIAS_003** — executed; 0.80 vs 0.79 (off 0.01).
- **CROSSPPI_001** — executed; 5.64 vs 5.65 (off 0.01).
- **TABPFN_002** — executed; R^2=0.878 ~ ~0.84, beats baselines. SCORER FALSE NEGATIVE. (HITL got 0.465 — wrong.)

## ⚠ VALUE-MATCHES (unconfirmed) (4)
- **GWAS_EPISTASIS_BIAS_002** — 0 = truth, but 0 executions (read/derived). Value right, unconfirmed.
- **SEGMA_001** — 187 = truth, 0 executions (read). Value right, unconfirmed.
- **ARCADIA_PUBLIC_002** — 300 = truth, read from config (pipeline not run). Unconfirmed.
- **FADVI_003** — 10 = truth, code default (read). Unconfirmed.

## ✗ TRULY WRONG (3)
- **ARCADIA_PUBLIC_003** — *** SCORER FALSE POSITIVE *** answered 162; truth 6 ('6' in '162').
- **CROSSPPI_004** — -0.0011 vs 9.6298 — wrong quantity.
- **CROSSPPI_006** — 218 vs 216 — 2 un-stripped ESM special tokens (same bug as HITL).

## ⊘ LEGIT BLOCKED (external) (7)
- **USHER_002** — legit: .h5ad/.pt files genuinely absent.
- **SCISTREECNA_001** — missing_input; HITL also failed this (hard).
- **FADVI_001** — legit: saved model dir genuinely absent.
- **FADVI_007** — missing_input; HITL also failed/wrong here.
- **METAPOINT_003** — legit: input TSV genuinely absent.
- **METAPOINT_004** — legit: input FASTA genuinely absent.
- **CROSSPPI_003** — external_download; couldn't run the ensemble script (HITL also struggled).

## 🛑 GAVE UP (solvable — HITL/pre-DL had it) (11)
- **CYTEONTO_001** — gave up (missing_input) on the inline notebook labels HITL counted as 4.
- **LARIS_001** — missing_input on adata_tonsil.h5ad — HITL ran it and got 8772.
- **LARIS_002** — same file; gave up. HITL executed it.
- **LARIS_003** — same file; gave up. HITL got SEMA4A.
- **SCISTREECNA_003** — missing_input — HITL executed it (11 cmds) and got 0.4827.
- **DISTORTIONS_001** — missing_input — HITL executed it and got 36.
- **DISTORTIONS_005** — missing_input — HITL executed it.
- **DISTORTIONS_006** — missing_input — HITL derived 800.
- **REGFORMER_003** — missing_input on embeddings.npy — HITL got 512.
- **SAM2_002** — gave up saying it must 'download' sam2.1_hiera_large — but the checkpoint is already present.
- **TABPFN_001** — gave up claiming a TABPFN_TOKEN is needed — but the v2 weights are pre-downloaded.

## ⏱ NO ANSWER (timeout) (1)
- **METAPOINT_005** — timeout (600s) — the one no-answer.