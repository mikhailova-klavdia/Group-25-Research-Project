# Summary

Run owner: Joao Victor  
Date: 2026-05-28  
Model: `gpt-5-mini-2025-08-07`  
Architecture: ReAct worker plus dependency/integrity critic

## Headline

| Paper | Correct | Total | Blocked |
|---|---:|---:|---:|
| PPLM | 0 | 6 | 6 |
| CrossPPI | 1 | 6 | 2 |
| metapointfinder | 2 | 5 | 3 |
| SKiM-GPT | 0 | 5 | 5 |
| **Total** | **3** | **22** | **16** |

Token/cost log from `papers/<slug>/costs.json`:

| Paper | Runs | Tokens | Estimated cost |
|---|---:|---:|---:|
| PPLM | 6 | 3,029,381 | $0.809858 |
| CrossPPI | 6 | 1,517,799 | $0.442527 |
| metapointfinder | 5 | 1,751,756 | $0.474486 |
| SKiM-GPT | 5 | 1,238,846 | $0.344425 |
| **Total** | **22** | **7,537,782** | **$2.071296** |

## Per-question status

| ID | Correct | Status | Blocker | Final answer preview |
|---|---:|---|---|---|
| PPLM_001 | false | blocked | missing_weights | Missing required affinity model weights file `weights/affinity_models.pkl`. |
| PPLM_002 | false | blocked | external_download | Required affinity model weights are absent and must be downloaded externally. |
| PPLM_003 | false | blocked | external_download | Could not download required PPLM model weights. |
| PPLM_004 | false | blocked | external_download | Could not download required PPLM model weights. |
| PPLM_005 | false | blocked | external_download | Required PPLM checkpoint could not be downloaded successfully. |
| PPLM_006 | false | blocked | external_download | Required PPI and PPLM pretrained weights are absent. |
| CROSSPPI_001 | false | answered | none | `5.72` |
| CROSSPPI_002 | false | blocked | external_download | ESM-2 pretrained model weights must be downloaded/loaded at runtime. |
| CROSSPPI_003 | true | answered | none | `8.20` |
| CROSSPPI_004 | false | answered | none | `-0.0011` |
| CROSSPPI_005 | false | blocked | missing_input | Repository lacks 3D coordinates needed for an 8 A distance contact-map count. |
| CROSSPPI_006 | false | answered | none | `218` |
| METAPOINT_001 | true | answered | none | `1182` |
| METAPOINT_002 | true | answered | none | `37` |
| METAPOINT_003 | false | blocked | missing_input | Required `sample_input.tsv` not found. |
| METAPOINT_004 | false | blocked | missing_input | Required `input_sequences.fasta` not found. |
| METAPOINT_005 | false | blocked | missing_input | Required `input_sequences.fasta` not found. |
| SKIMGPT_001 | false | blocked | missing_input | Required wrapper output directory not found. |
| SKIMGPT_002 | false | blocked | missing_input | Required test iterations directory not found. |
| SKIMGPT_003 | false | blocked | missing_input | Required wrapper output directory not found. |
| SKIMGPT_004 | false | blocked | missing_input | Required wrapper output directory not found. |
| SKIMGPT_005 | false | blocked | missing_input | Required DCH output directory not found. |

## Notes

- This run is stricter than earlier sweeps: many cases that previously guessed or reused README values now return structured blocked answers with evidence.
- `CROSSPPI_003` is the strongest positive result: the agent executed inference and produced `8.20`, matching the ground truth.
- `CROSSPPI_006` still failed on the known BOS/EOS-token issue: the agent returned `218` instead of the residue-count answer `216`.
- Most remaining failures are missing external weights, missing benchmark data directories, or unavailable structural inputs rather than random hallucinations.
