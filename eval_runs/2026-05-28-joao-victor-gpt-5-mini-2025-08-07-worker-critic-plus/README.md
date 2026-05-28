# Worker-Critic-Plus Sweep

- Owner: Joao Victor
- Date: 2026-05-28
- Model: `gpt-5-mini-2025-08-07`
- Team: `worker-critic-plus`
- Questions: 22
- Correct: 8 / 22
- Total tokens: 8,734,917
- Estimated cost: $2.38431

## Files

- `chains/`: copied chain JSON outputs for the 22 questions in this sweep.
- `logs/`: terminal logs for the four paper-level commands.
- `costs/`: copied per-paper `costs.json` files used for the token and cost totals above.

## Breakdown

| Paper | Correct | Total |
| --- | ---: | ---: |
| PPLM | 3 | 6 |
| CrossPPI | 1 | 6 |
| metapointfinder | 4 | 5 |
| SKiM-GPT | 0 | 5 |

## Comparison Baseline

The colleague/Karthik worker+critic sweep had 3 / 22 honestly correct:
`CROSSPPI_003`, `METAPOINT_001`, and `METAPOINT_002`.

This worker-critic-plus sweep kept those three and added:
`PPLM_003`, `PPLM_004`, `PPLM_006`, `METAPOINT_004`, and `METAPOINT_005`.

## Per-Question Results

| ID | Correct | Final answer |
| --- | --- | --- |
| PPLM_001 | false | EXECUTION_REQUIRED: missing `weights/affinity_models.pkl` after Google Drive rate limit |
| PPLM_002 | false | EXECUTION_REQUIRED: missing `weights/affinity_models.pkl` |
| PPLM_003 | true | `(122, 1280)` |
| PPLM_004 | true | `-0.000396` |
| PPLM_005 | false | missing `PPLM/notebooks/run_pplm/checkpoints/pplm.ckpt` |
| PPLM_006 | true | `0.9431081` |
| CROSSPPI_001 | false | `5.64` |
| CROSSPPI_002 | false | EXECUTION_REQUIRED: missing usable local pretrained weights/artifacts |
| CROSSPPI_003 | true | `8.20 pKD` |
| CROSSPPI_004 | false | `-0.0011` |
| CROSSPPI_005 | false | `220` |
| CROSSPPI_006 | false | `218 residues` |
| METAPOINT_001 | true | `1182 sequences` |
| METAPOINT_002 | true | `37` |
| METAPOINT_003 | false | `100 sequences` |
| METAPOINT_004 | true | `5000 bp` |
| METAPOINT_005 | true | `10000 bp` |
| SKIMGPT_001 | false | missing `skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output_skim` |
| SKIMGPT_002 | false | missing `skimgpt/notebooks/eval_json_results/data/test_iterations` |
| SKIMGPT_003 | false | missing `skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output` |
| SKIMGPT_004 | false | missing `skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output` |
| SKIMGPT_005 | false | missing `skimgpt/notebooks/eval_json_results/data/test_dch_output` |
