# Human-in-the-Loop Sweep — FINAL

- Model: `gpt-5-mini-2025-08-07` · Team: `human-in-the-loop`
- Config: `--fresh-venv-per-question --max-turns 50`, 10-min wall-clock cap/question
- Questions: **46/46** · Captured spend: **$8.45** (excludes 7 no-answer runs' API cost)
- Artifacts: 39 chains, 46 logs, manifest.csv (46 rows), sweep_plan.json

## Outcome

| Category | Count |
|---|---|
| ✅ correct | 19 |
| 🟦 blocked-but-correct | 4 |
| ❗ genuinely wrong | 7 |
| 🟥 blocked-wrong / no-value | 9 |
| ⏱️ no-answer (timeout/error) | 7 |

**Effectively right: 23/46** · genuinely wrong: 7


### ✅ Correct (19)
- `GWAS_EPISTASIS_BIAS_001` — truth `5.036982e-08`
- `SENTIEON_CLI_001` — truth `CONSERVATIVE`
- `GWPROT_001` — truth `54`
- `LARIS_001` — truth `8772`
- `LARIS_003` — truth `SEMA4A`
- `SC_FRAMEWORK_001` — truth `5000`
- `SCISTREECNA_003` — truth `0.4827586206896552`
- `DISTORTIONS_001` — truth `36`
- `ARCADIA_PUBLIC_002` — truth `300`
- `ARCADIA_PUBLIC_003` — truth `6`
- `REGFORMER_002` — truth `0.8841`
- `REGFORMER_003` — truth `512`
- `FADVI_003` — truth `10`
- `PPLM_002` — truth `Favorable`
- `PPLM_003` — truth `(122, 1280)`
- `PPLM_005` — truth `(660, 122, 70)`
- `PPLM_006` — truth `0.94310874`
- `METAPOINT_002` — truth `37`
- `METAPOINT_005` — truth `10000`

### 🟦 Blocked but correct (4)
- `CYTEONTO_001` — truth `4`
- `CYTEONTO_002` — truth `stem cell`
- `GWPROT_002` — truth `4`
- `DISTORTIONS_006` — truth `800`

### ❗ Genuinely wrong (got vs truth) (7)
- `LARIS_002` — truth `1985`, got `2951`
- `DISTORTIONS_005` — truth `6`, got `9`
- `CROSSPPI_001` — truth `5.65`, got `5.64`
- `CROSSPPI_003` — truth `8.20`, got `7.77`
- `CROSSPPI_006` — truth `216`, got `218`
- `SAM2_001` — truth `~52 masks`, got `Generated 3 masks (shape (3, 534, 800)) `
- `SAM2_002` — truth `~54 masks`, got `Generated masks saved to workspace/masks`

### 🟥 Blocked-wrong / no value (9)
- `GWAS_EPISTASIS_BIAS_003` — truth `0.79`
- `USHER_002` — truth `64603`
- `FADVI_001` — truth `30`
- `FADVI_007` — truth `30`
- `PPLM_001` — truth `-8.226562`
- `METAPOINT_003` — truth `20`
- `METAPOINT_004` — truth `5000`
- `CROSSPPI_004` — truth `9.6298`
- `TABPFN_002` — truth `~0.84 R^2 / ~0.45 RMSE; beats LinReg and RandomForest`

### ⏱️ No answer (7)
- `CYTEONTO_003` — timeout
- `GWAS_EPISTASIS_BIAS_002` — timeout
- `SEGMA_001` — timeout
- `SCISTREECNA_001` — exit_1
- `PPLM_004` — timeout
- `METAPOINT_001` — timeout
- `TABPFN_001` — timeout