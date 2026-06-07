# Manual Correctness Audit — Worker-Critic-Plus-Plus (46 questions)

Hand-verified against each chain. Corrects for scorer false-positives and categorises blocked answers.

**Verdicts:**
- ✓ Correct — executed and confirmed
- ✗ Wrong — committed to a wrong answer
- ⊘ Legit blocked — data/artifacts genuinely absent from repo
- 🛑 Integrity-guard block — critic or guard rejected answer that may have been achievable

| ID | Scorer | Audit verdict | Final answer | Ground truth | Notes |
|---|---|---|---|---|---|
| ARCADIA_PUBLIC_001 | ✓ | ✓ Correct | 300 | 300 | Read directly from config |
| ARCADIA_PUBLIC_002 | ✓ | ✗ Wrong | 162 | 6 | **Scorer false-positive** — "6" is a substring of "162"; agent returned 162 which is incorrect |
| CROSSPPI_001 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 5.65 | torch/esm not installable in environment |
| CROSSPPI_002 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 8.20 | pandas/dependency install failed |
| CROSSPPI_003 | ✗ | ✗ Wrong | -0.0115 | 9.6298 | Ran wrong calculation; order-of-magnitude off |
| CROSSPPI_004 | ✗ | ✗ Wrong | 218 | 216 | Off by 2; likely un-stripped ESM-2 special tokens (same issue as João's CROSSPPI_006) |
| CYTEONTO_001 | ✓ | ✓ Correct | 4 | 4 | Read from CSV |
| CYTEONTO_002 | ✓ | ✓ Correct | stem cell | stem cell | Read from CSV |
| CYTEONTO_003 | ✓ | ✓ Correct | ovum | ovum | Read from CSV |
| DISTORTIONS_001 | ✓ | ✓ Correct | 36 | 36 | Executed successfully |
| DISTORTIONS_002 | ✗ | ✗ Wrong | 7 | 6 | Off by 1; miscounted or wrong grouping |
| DISTORTIONS_003 | ✓ | ✓ Correct | 800 | 800 | Executed successfully |
| FADVI_001 | ✓ | ✓ Correct | 30 | 30 | Executed successfully |
| FADVI_002 | ✓ | ✓ Correct | 10 | 10 | Executed successfully |
| FADVI_003 | ✓ | ✓ Correct | 30 | 30 | Executed successfully |
| GWAS_EPISTASIS_BIAS_001 | ✓ | ✓ Correct | 5.03698e-08 | 5.036982e-08 | Same value, different float formatting |
| GWAS_EPISTASIS_BIAS_002 | ✓ | ✓ Correct | 0 | 0 | Executed successfully |
| GWAS_EPISTASIS_BIAS_003 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 0.79 | Agent planned to run modified simulation but did not execute; solvable in principle |
| GWPROT_001 | ✓ | ✓ Correct | 54 | 54 | Executed successfully |
| GWPROT_002 | ✓ | ✓ Correct | 4 unique ligand types | 4 | Correct value; scorer matches "4" in answer string |
| LARIS_001 | ✓ | ✓ Correct | 8772 | 8772 | Executed successfully |
| LARIS_002 | ✓ | ✓ Correct | 1985 | 1985 | Executed successfully |
| LARIS_003 | ✓ | ✓ Correct | SEMA4A | SEMA4A | Executed successfully |
| METAPOINTFINDER_001 | ✓ | ✓ Correct | 1182 | 1182 | Executed successfully |
| METAPOINTFINDER_002 | ✓ | ✓ Correct | 37 | 37 | Executed successfully |
| METAPOINTFINDER_003 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 20 | Input file `sample_input.tsv` absent from repo |
| METAPOINTFINDER_004 | ✓ | ✓ Correct | 5000 | 5000 | Executed successfully |
| METAPOINTFINDER_005 | ✓ | ✓ Correct | 10000 bp | 10000 | Correct value; scorer matches "10000" in answer string |
| PPLM_001 | ✗ | ✗ Wrong | -7.609 kcal/mol | -8.226562 | Wrong binding energy; different execution path |
| PPLM_002 | ✓ | ✓ Correct | Favorable | Favorable | Executed successfully |
| PPLM_003 | ✗ | ✗ Wrong | (122, 320) | (122, 1280) | Wrong embedding dim; got 320 instead of 1280 |
| PPLM_004 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | -0.000396 | Pretrained model file `pplm_t33_650M.pt` absent |
| PPLM_005 | ✓ | ✓ Correct | (660, 122, 70) | (660, 122, 70) | Executed successfully |
| PPLM_006 | ✗ | 🛑 Integrity-guard block | EXECUTION_REQUIRED | 0.94310874 | Critic rejected answer as ungrounded in execution; João's worker-critic got this correct (0.9431081) |
| REGFORMER_001 | ✓ | ✓ Correct | 0.8841 | 0.8841 | Executed successfully |
| REGFORMER_002 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 512 | Required embedding/data files absent from repo |
| SAM2_001 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | ~52 masks | PIL/numpy/torch not installable in environment |
| SAM2_002 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | ~54 masks | torch/hydra-core not installable in environment |
| SCISTREECNA_001 | ✗ | ✗ Wrong | 0.38596 | 0.37931 | Close but wrong; different rounding or code path |
| SCISTREECNA_002 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 0.48276 | CuPy/GPU required; not available in environment |
| SC_FRAMEWORK_001 | ✓ | ✓ Correct | 5000 cells | 5000 | Executed successfully |
| SEGMA_001 | ✓ | ✓ Correct | 187 amino acids | 187 | Executed successfully |
| SENTIEON_CLI_001 | ✓ | ✓ Correct | CONSERVATIVE | CONSERVATIVE | Read from output |
| TABPFN_001 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | ~0.97 acc | TabPFN requires license token not present in environment |
| TABPFN_002 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | ~0.84 R² | Dependency mismatch; environment could not be set up |
| USHER_001 | ✗ | ⊘ Legit blocked | EXECUTION_REQUIRED | 64603 | Required .h5ad files and alignment_model.pt absent from repo |

## Summary (after audit corrections)

| Verdict | Count |
|---|---|
| ✓ Correct | 26 |
| ✗ Wrong | 7 |
| ⊘ Legit blocked | 12 |
| 🛑 Integrity-guard block | 1 |

- **Correct: 26 / 46** after removing ARCADIA_PUBLIC_002 scorer false-positive (scorer said 27).
- **Truly wrong: 7** (CROSSPPI_003, CROSSPPI_004, DISTORTIONS_002, PPLM_001, PPLM_003, SCISTREECNA_001, + ARCADIA_PUBLIC_002 false-positive).
- **PPLM_006** is a special case: the integrity guard blocked an answer that João's worker-critic got right — the plus-plus prompt's stricter execution-grounding requirement cost one correct answer here.
