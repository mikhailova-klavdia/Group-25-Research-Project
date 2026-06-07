# README-assisted vs autonomous baseline


## worker-critic
- re-run questions: 46 | help_provided: 46/46 | cost $6.70
- scorer tally: correct=29 wrong=7 blocked=10 missing=0
- **recovered (baseline wrong/blocked -> re-run correct): 9**
    + CROSSPPI_003: was blocked -> now correct (8.20)
    + CROSSPPI_006: was wrong -> now correct (216)
    + CYTEONTO_001: was blocked -> now correct (4)
    + DISTORTIONS_005: was blocked -> now correct (6)
    + DISTORTIONS_006: was blocked -> now correct (800)
    + METAPOINT_004: was blocked -> now correct (5000 bp)
    + METAPOINT_005: was MISSING -> now correct (10000 bp)
    + SAM2_001: was wrong -> now correct (52 masks)
    + SAM2_002: was blocked -> now correct (54 masks)
- **regressed (baseline correct -> re-run wrong/blocked): 1**
    - FADVI_003: was correct -> now blocked (Required file 'fadvi/notebooks/advanced_usage/data)

## worker-critic-plus-plus
- re-run questions: 46 | help_provided: 46/46 | cost $3.55
- scorer tally: correct=33 wrong=8 blocked=5 missing=0
- **recovered (baseline wrong/blocked -> re-run correct): 10**
    + CROSSPPI_003: was wrong -> now correct (8.20 pKD)
    + CROSSPPI_006: was wrong -> now correct (216)
    + GWAS_EPISTASIS_BIAS_003: was blocked -> now correct (0.79)
    + PPLM_001: was wrong -> now correct (-8.2265625 kcal/mol)
    + PPLM_003: was wrong -> now correct ((122, 1280))
    + PPLM_004: was blocked -> now correct (-0.000396)
    + PPLM_006: was blocked -> now correct (0.9431081)
    + REGFORMER_003: was blocked -> now correct (512)
    + SAM2_001: was blocked -> now correct (52 masks)
    + SAM2_002: was blocked -> now correct (54)
- **regressed (baseline correct -> re-run wrong/blocked): 3**
    - DISTORTIONS_001: was correct -> now wrong (8)
    - LARIS_003: was correct -> now blocked (EXECUTION_REQUIRED — the required AnnData file tes)
    - METAPOINT_002: was correct -> now wrong (19)