# Per-question correctness audit (manual, verified against the chains)

gpt-5-mini · human-in-the-loop · 46 questions. **Re-verified** — two earlier 'near-miss' calls were corrected to wrong, two 'correct' downgraded to value-matches-unverified.

## True tally

| Verdict | Count |
|---|---|
| ✓ TRUE CORRECT | 19 |
| ≈ NEAR-MISS (effectively right) | 2 |
| ⚠ VALUE MATCHES BUT NOT EXECUTION-CONFIRMED | 2 |
| ✗ TRUE WRONG | 12 |
| ⊘ LEGIT BLOCKED (external) | 4 |
| ⏱ NO ANSWER (timeout/error) | 7 |

**Solid correct: 19** · near-miss (effectively right): 2 · value-matches-unverified: 2 · truly wrong: 12 · external blocks: 4 · no-answer: 7

- **Effectively right (solid + near-miss): 21/46.** Up to 23 if the 2 value-matches-unverified are counted.


## ✓ TRUE CORRECT (19)
- **CYTEONTO_001** — Derived 4 from adv_tutorial.ipynb (CSV absent); guard-downgraded. Verified: notebook list has 4.
- **CYTEONTO_002** — Derived 'stem cell' (first of algorithm1_labels) from notebook; guard-downgraded. Verified.
- **GWAS_EPISTASIS_BIAS_001** — Executed (2 cmds); 5.0369820e-08 = truth.
- **SENTIEON_CLI_001** — dry_run; CONSERVATIVE = truth (config read; dry-run doesn't execute).
- **GWPROT_001** — Verified: find_repo_files listed the KRAS Proteins dir; counted 54 .pdb = truth. Legit file-count answer.
- **GWPROT_002** — Verified: read the ligand CSV, counted 4 unique ligand codes = truth; guard-downgraded for no exec.
- **LARIS_003** — SEMA4A = truth.
- **SC_FRAMEWORK_001** — Executed; 5000 cells = truth.
- **SCISTREECNA_003** — 11 executions; 0.4827586206896552 exact. Cleanest run.
- **DISTORTIONS_001** — Executed; 36 = truth.
- **DISTORTIONS_006** — Derived 800 = truth (agent reports script produced 800); guard-downgraded. Value matches; execution-grounding only partly confirmed.
- **REGFORMER_002** — 0.8841 = truth.
- **REGFORMER_003** — 512 = truth.
- **FADVI_003** — 10 = truth, read from code default n_latent_r=10 (inspection, not execution). Value right, method soft.
- **PPLM_002** — Executed; 'Favorable' = truth.
- **PPLM_003** — 2 executions; (122,1280) = truth.
- **PPLM_006** — 2 executions; 0.9431081 ≈ truth 0.94310874.
- **METAPOINT_002** — 3 executions; 37 = truth.
- **METAPOINT_005** — 3 executions; 10000 bp = truth.

## ≈ NEAR-MISS (effectively right) (2)
- **LARIS_001** — Executed; 8774 vs 8772 (off by 2). Scorer accepted on tolerance; effectively right, marginally off.
- **CROSSPPI_001** — Verified: real model output 5.644943 -> reported 5.64 vs truth 5.65. Same value at the rounding boundary; effectively correct.

## ⚠ VALUE MATCHES BUT NOT EXECUTION-CONFIRMED (2)
- **ARCADIA_PUBLIC_002** — [DOWNGRADED] 300 = truth but READ from configs/config.json — pipeline was NOT run. Value matches but may be coincidental; not confirmed by execution.
- **PPLM_005** — [DOWNGRADED] (660,122,70) = truth exactly, but NO successful execution captured — likely derived from architecture + seq lengths. Value matches; not execution-confirmed.

## ✗ TRUE WRONG (12)
- **GWAS_EPISTASIS_BIAS_003** — [CORRECTED from near-miss] Simulation script CRASHED (exit 2, workspace/workspace path bug); 0.80 was an unverified guess, never computed. Wrong.
- **LARIS_002** — 2951 vs 1985 with ZERO successful execs — guessed. Wrong.
- **DISTORTIONS_005** — Executed but 9 vs 6.
- **ARCADIA_PUBLIC_003** — Scorer FALSE POSITIVE: 162 vs truth 6 ('6' is a substring of '162'). Wrong.
- **FADVI_007** — Derived 70 vs 30; guard-downgraded. Underlying value wrong.
- **PPLM_001** — Affinity -10.66 vs -8.23; mis-predicted.
- **CROSSPPI_003** — 7.77 vs 8.20; 0 successful execs in 25 steps — struggled, wrong.
- **CROSSPPI_004** — Derived -0.0369 vs 9.6298 — wrong quantity; guard-downgraded.
- **CROSSPPI_006** — [CORRECTED from near-miss] Embedding shape (218,1280) = 216 residues + 2 ESM-2 special tokens NOT stripped. Truth 216. Special-token bug -> wrong.
- **SAM2_001** — 3 masks vs ~52 (wrong mode: single-prompt, not the automatic generator).
- **SAM2_002** — 3 masks vs ~54 (same wrong-mode issue).
- **TABPFN_002** — R^2=0.465 vs ~0.84; guard-downgraded. Underperforms.

## ⊘ LEGIT BLOCKED (external) (4)
- **USHER_002** — Legit block: required .h5ad + alignment_model.pt genuinely absent (missing_input).
- **FADVI_001** — Legit block: saved model dir fadvi_save/ genuinely absent (missing_input).
- **METAPOINT_003** — Legit block: input TSV genuinely missing (missing_input).
- **METAPOINT_004** — Legit block: input FASTA genuinely missing (missing_input).

## ⏱ NO ANSWER (timeout/error) (7)
- **CYTEONTO_003** — Timeout (600s).
- **GWAS_EPISTASIS_BIAS_002** — Timeout (600s).
- **SEGMA_001** — Timeout (600s).
- **SCISTREECNA_001** — Turn-limit / error (exit 1) after 422s.
- **PPLM_004** — Timeout (600s).
- **METAPOINT_001** — Timeout (600s).
- **TABPFN_001** — Timeout (600s).