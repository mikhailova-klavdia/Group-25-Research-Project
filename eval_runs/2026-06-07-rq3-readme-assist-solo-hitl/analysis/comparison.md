# README-assisted vs autonomous baseline


## solo
- re-run questions: 46 | help_provided: 46/46 | cost $4.74
- scorer tally: correct=25 wrong=7 blocked=14 missing=0
- **recovered (baseline wrong/blocked -> re-run correct): 9**
    + CROSSPPI_003: was blocked -> now correct (8.20)
    + CROSSPPI_006: was wrong -> now correct (216)
    + DISTORTIONS_005: was blocked -> now correct (6)
    + GWAS_EPISTASIS_BIAS_001: was blocked -> now correct (5.0369820092655004e-08)
    + GWAS_EPISTASIS_BIAS_002: was blocked -> now correct (0)
    + GWAS_EPISTASIS_BIAS_003: was MISSING -> now correct (0.79)
    + LARIS_002: was blocked -> now correct (1985)
    + METAPOINT_004: was MISSING -> now correct (5000 bp)
    + SEGMA_001: was blocked -> now correct (187 amino acids)
- **regressed (baseline correct -> re-run wrong/blocked): 2**
    - METAPOINT_001: was correct -> now wrong (312)
    - METAPOINT_002: was correct -> now wrong (38)

## human-in-the-loop
- re-run questions: 45 | help_provided: 45/45 | cost $9.04
- scorer tally: correct=29 wrong=6 blocked=10 missing=0
- **recovered (baseline wrong/blocked -> re-run correct): 12**
    + CROSSPPI_006: was wrong -> now correct (216)
    + CYTEONTO_002: was blocked -> now correct (stem cell)
    + DISTORTIONS_006: was blocked -> now correct (800 cells)
    + FADVI_001: was blocked -> now correct (30)
    + GWAS_EPISTASIS_BIAS_002: was MISSING -> now correct (0)
    + GWPROT_002: was blocked -> now correct (4)
    + METAPOINT_001: was MISSING -> now correct (1182 sequences)
    + PPLM_001: was blocked -> now correct (-8.2265625 kcal/mol)
    + PPLM_004: was MISSING -> now correct (-0.000396)
    + SAM2_001: was wrong -> now correct (52 masks)
    + SAM2_002: was wrong -> now correct (54)
    + SEGMA_001: was MISSING -> now correct (187 amino acids)
- **regressed (baseline correct -> re-run wrong/blocked): 1**
    - REGFORMER_003: was correct -> now blocked (EXECUTION_REQUIRED — the required data files RegFo)