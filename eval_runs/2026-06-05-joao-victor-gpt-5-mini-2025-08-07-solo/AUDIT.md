# Solo — per-question correctness audit (verified vs chains)

gpt-5-mini · solo · 46 questions.

## True tally

| Verdict | Count |
|---|---|
| ✓ TRUE CORRECT | 15 |
| ≈ NEAR-MISS | 0 |
| ⚠ VALUE-MATCHES (unconfirmed) | 2 |
| ✗ TRULY WRONG | 4 |
| ⊘ LEGIT BLOCKED (external) | 6 |
| 🛑 GAVE UP (solvable — others had it) | 17 |
| ⏱ NO ANSWER (timeout) | 2 |

**Effectively right: 17/46** (15 solid + 2 value-matches) · truly wrong: 4


## ✓ TRUE CORRECT (15)
- **CYTEONTO_002** — stem cell = truth (read from notebook).
- **CYTEONTO_003** — ovum = truth.
- **GWPROT_001** — counted 54 PDBs = truth.
- **GWPROT_002** — 4 = truth (counted ligand codes).
- **METAPOINT_001** — 2 execs; 1182 = truth.
- **METAPOINT_002** — 2 execs; 37 = truth.
- **PPLM_001** — 3 execs; -8.2265625 = truth.
- **PPLM_002** — 3 execs; Favorable = truth.
- **PPLM_003** — 3 execs; (122,1280) = truth.
- **PPLM_004** — 5 execs; -0.000396 = truth.
- **PPLM_005** — 5 execs; (660,122,70) = truth (execution-grounded).
- **PPLM_006** — 3 execs; 0.9431081 ~ truth.
- **REGFORMER_002** — 0.8841 = truth (read result file).
- **SC_FRAMEWORK_001** — 2 execs; 5000 = truth.
- **SENTIEON_CLI_001** — CONSERVATIVE = truth (dry-run).

## ≈ NEAR-MISS (0)

## ⚠ VALUE-MATCHES (unconfirmed) (2)
- **ARCADIA_PUBLIC_002** — 300 = truth, but read from config, no execution. Unconfirmed.
- **DISTORTIONS_006** — 800 = truth, read (no execution). Unconfirmed.

## ✗ TRULY WRONG (4)
- **ARCADIA_PUBLIC_003** — *** SCORER FALSE POSITIVE *** answered 162; truth 6 ('6' in '162').
- **CROSSPPI_004** — -0.0011 vs 9.6298 — wrong quantity.
- **CROSSPPI_006** — 218 vs 216 — 2 un-stripped ESM special tokens (same bug as the others).
- **SAM2_002** — generated 322 masks vs ~54 — wrong params/config.

## ⊘ LEGIT BLOCKED (external) (6)
- **CROSSPPI_003** — external_download; couldn't run the ensemble script (HITL/WC also struggled).
- **FADVI_001** — legit: saved model dir genuinely absent.
- **FADVI_007** — missing_input; HITL/WC also failed here.
- **METAPOINT_003** — legit: input TSV genuinely absent.
- **SCISTREECNA_001** — missing_input; HITL also failed this.
- **USHER_002** — legit: .h5ad/.pt files genuinely absent.

## 🛑 GAVE UP (solvable — others had it) (17)
- **CROSSPPI_001** — gave up (external_download) — worker-critic executed this and got 5.64.
- **CYTEONTO_001** — gave up (missing_input) on the inline notebook labels HITL counted as 4.
- **DISTORTIONS_001** — missing_input — HITL executed this and got 36.
- **DISTORTIONS_005** — missing_input — HITL executed this.
- **FADVI_003** — missing_input — HITL/WC read the code default (10); Solo gave up.
- **GWAS_EPISTASIS_BIAS_001** — gave up (external_download) — HITL/WC executed this and got 5.04e-08.
- **GWAS_EPISTASIS_BIAS_002** — could not install numpy — Solo has NO install-retry, so a dep gap = a give-up (WC got 0).
- **LARIS_001** — missing_input on adata_tonsil.h5ad — HITL got 8772.
- **LARIS_002** — same file; HITL ran it.
- **LARIS_003** — same file; HITL got SEMA4A.
- **METAPOINT_005** — missing_input — worker-critic got 10000 here.
- **REGFORMER_003** — missing_input on embeddings.npy — HITL got 512.
- **SAM2_001** — missing_dependency (couldn't install PIL etc., no install-retry) — WC got 52 masks.
- **SCISTREECNA_003** — missing_input — HITL executed this and got 0.4827.
- **SEGMA_001** — claimed gpu_required and gave up — WC got 187 on CPU.
- **TABPFN_001** — claimed a license/token is needed — but the v2 weights are pre-downloaded.
- **TABPFN_002** — same license claim — WC trained it and got R^2=0.88.

## ⏱ NO ANSWER (timeout) (2)
- **GWAS_EPISTASIS_BIAS_003** — timeout (600s).
- **METAPOINT_004** — timeout (600s).