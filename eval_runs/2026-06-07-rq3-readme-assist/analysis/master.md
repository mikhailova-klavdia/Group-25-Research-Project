# Consolidated master — both teams by paper


## ARCADIA_PUBLIC
- WC ARCADIA_PUBLIC_002: GT='300'
    -> [answered|scorer=True] 300
- WC ARCADIA_PUBLIC_003: GT='6'
    -> [answered|scorer=True] 162
- PP ARCADIA_PUBLIC_001: GT='300'
    -> [answered|scorer=True] 300
- PP ARCADIA_PUBLIC_002: GT='6'
    -> [answered|scorer=True] 162

## CROSSPPI
- WC CROSSPPI_001: GT='5.65'
    -> [answered|scorer=False] 5.64
- WC CROSSPPI_003: GT='8.20'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — running the repository's inference script t.py is
- WC CROSSPPI_004: GT='9.6298'
    -> [answered|scorer=False] -0.0011
- WC CROSSPPI_006: GT='216'
    -> [answered|scorer=False] 218
- PP CROSSPPI_001: GT='5.65'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — required packages (torch and esm) are not availab
- PP CROSSPPI_002: GT='8.20'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — missing dependencies prevented running the infere
- PP CROSSPPI_003: GT='9.6298'
    -> [answered|scorer=False] -0.0115
- PP CROSSPPI_004: GT='216'
    -> [answered|scorer=False] 218

## CYTEONTO
- WC CYTEONTO_001: GT='4'
    -> [blocked|scorer=False] Required file 'CyteOnto/notebooks/adv_tutorial/data/author_labels.csv'
- WC CYTEONTO_002: GT='stem cell'
    -> [answered|scorer=True] stem cell
- WC CYTEONTO_003: GT='ovum'
    -> [answered|scorer=True] ovum
- PP CYTEONTO_001: GT='4'
    -> [answered|scorer=True] 4
- PP CYTEONTO_002: GT='stem cell'
    -> [answered|scorer=True] stem cell
- PP CYTEONTO_003: GT='ovum'
    -> [answered|scorer=True] ovum

## DISTORTIONS
- WC DISTORTIONS_001: GT='36'
    -> [blocked|scorer=False] Required file 'distortions/notebooks/c_elegans/data/c_elegans_metadata
- WC DISTORTIONS_005: GT='6'
    -> [blocked|scorer=False] Required file 'distortions/notebooks/pbmc/data/data/pbmc3k_processed.h
- WC DISTORTIONS_006: GT='800'
    -> [blocked|scorer=False] Required files 'distortions/notebooks/c_elegans/data/c_elegans_data.cs
- PP DISTORTIONS_001: GT='36'
    -> [answered|scorer=True] 36
- PP DISTORTIONS_002: GT='6'
    -> [answered|scorer=False] 7
- PP DISTORTIONS_003: GT='800'
    -> [answered|scorer=True] 800

## FADVI
- WC FADVI_001: GT='30'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — need to load the pretrained model file from repo 
- WC FADVI_003: GT='10'
    -> [answered|scorer=True] 10
- WC FADVI_007: GT='30'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — Required data files 'fadvi/notebooks/spatial_and_
- PP FADVI_001: GT='30'
    -> [answered|scorer=True] 30
- PP FADVI_002: GT='10'
    -> [answered|scorer=True] 10
- PP FADVI_003: GT='30'
    -> [answered|scorer=True] 30

## GWAS_EPISTASIS_BIAS
- WC GWAS_EPISTASIS_BIAS_001: GT='5.036982e-08'
    -> [answered|scorer=True] 5.0369820092655004e-08
- WC GWAS_EPISTASIS_BIAS_002: GT='0'
    -> [answered|scorer=True] 0
- WC GWAS_EPISTASIS_BIAS_003: GT='0.79'
    -> [answered|scorer=False] 0.80
- PP GWAS_EPISTASIS_BIAS_001: GT='5.036982e-08'
    -> [answered|scorer=True] 5.03698201089221e-08
- PP GWAS_EPISTASIS_BIAS_002: GT='0'
    -> [answered|scorer=True] 0
- PP GWAS_EPISTASIS_BIAS_003: GT='0.79'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — I intended to run a modified simulation script bu

## GWPROT
- WC GWPROT_001: GT='54'
    -> [answered|scorer=True] 54
- WC GWPROT_002: GT='4'
    -> [answered|scorer=True] 4
- PP GWPROT_001: GT='54'
    -> [answered|scorer=True] 54
- PP GWPROT_002: GT='4'
    -> [answered|scorer=True] 4 unique ligand types

## LARIS
- WC LARIS_001: GT='8772'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — required AnnData file 'LARIS/notebooks/04_laris_t
- WC LARIS_002: GT='1985'
    -> [blocked|scorer=False] Required file 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_d
- WC LARIS_003: GT='SEMA4A'
    -> [blocked|scorer=False] Required file 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_d
- PP LARIS_001: GT='8772'
    -> [answered|scorer=True] 8772
- PP LARIS_002: GT='1985'
    -> [answered|scorer=True] 1985
- PP LARIS_003: GT='SEMA4A'
    -> [answered|scorer=True] SEMA4A

## METAPOINT
- WC METAPOINT_001: GT='1182'
    -> [answered|scorer=True] 1182
- WC METAPOINT_002: GT='37'
    -> [answered|scorer=True] 37
- WC METAPOINT_003: GT='20'
    -> [blocked|scorer=False] Required file 'metapointfinder/notebooks/make_dna_mutants/output/sampl
- WC METAPOINT_004: GT='5000'
    -> [blocked|scorer=False] Required file 'metapointfinder/notebooks/pad_to_10kb/data/input_sequen
- PP METAPOINTFINDER_001: GT='1182'
    -> [answered|scorer=True] 1182
- PP METAPOINTFINDER_002: GT='37'
    -> [answered|scorer=True] 37
- PP METAPOINTFINDER_003: GT='20'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — the specified input file metapointfinder/notebook
- PP METAPOINTFINDER_004: GT='5000'
    -> [answered|scorer=True] 5000
- PP METAPOINTFINDER_005: GT='10000'
    -> [answered|scorer=True] 10000 bp

## PPLM
- WC PPLM_001: GT='-8.226562'
    -> [answered|scorer=True] -8.2265625 kcal/mol
- WC PPLM_002: GT='Favorable'
    -> [answered|scorer=True] favorable (predicted affinity = -8.2265625)
- WC PPLM_003: GT='(122, 1280)'
    -> [answered|scorer=True] (122, 1280)
- WC PPLM_004: GT='-0.000396'
    -> [answered|scorer=True] -0.000396
- WC PPLM_005: GT='(660, 122, 70)'
    -> [answered|scorer=True] (660, 122, 70)
- WC PPLM_006: GT='0.94310874'
    -> [answered|scorer=True] 0.9431081
- PP PPLM_001: GT='-8.226562'
    -> [answered|scorer=False] -7.6090136 kcal/mol
- PP PPLM_002: GT='Favorable'
    -> [answered|scorer=True] Favorable
- PP PPLM_003: GT='(122, 1280)'
    -> [answered|scorer=False] (122, 320)
- PP PPLM_004: GT='-0.000396'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — pretrained model file pplm/models/pplm_t33_650M.p
- PP PPLM_005: GT='(660, 122, 70)'
    -> [answered|scorer=True] (660, 122, 70)
- PP PPLM_006: GT='0.94310874'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — Auto-flagged by the integrity guard: this answer 

## REGFORMER
- WC REGFORMER_002: GT='0.8841'
    -> [answered|scorer=True] 0.8841
- WC REGFORMER_003: GT='512'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — Required file 'RegFormer/notebooks/cell_emb/data/
- PP REGFORMER_001: GT='0.8841'
    -> [answered|scorer=True] 0.8841
- PP REGFORMER_002: GT='512'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — required data files (RegFormer/notebooks/cell_emb

## SAM2
- WC SAM2_001: GT='~52 masks'
    -> [answered|scorer=False] Generated 52 masks for notebooks/images/groceries.jpg using sam2.1_hie
- WC SAM2_002: GT='~54 masks'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — need to run the model with the specified checkpoi
- PP SAM2_001: GT='~52 masks'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — execution blocked by missing Python packages in t
- PP SAM2_002: GT='~54 masks'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — required dependencies (torch, hydra-core/omegacon

## SCISTREECNA
- WC SCISTREECNA_001: GT='0.3793103448275862'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — Required input files referenced in the question a
- WC SCISTREECNA_003: GT='0.4827586206896552'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — Required data files 'ScisTreeCNA/notebooks/scistr
- PP SCISTREECNA_001: GT='0.3793103448275862'
    -> [answered|scorer=False] 0.38596491228070173
- PP SCISTREECNA_002: GT='0.4827586206896552'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — The execution environment lacks CuPy/NVIDIA GPU s

## SC_FRAMEWORK
- WC SC_FRAMEWORK_001: GT='5000'
    -> [answered|scorer=True] 5000
- PP SC_FRAMEWORK_001: GT='5000'
    -> [answered|scorer=True] 5000 cells

## SEGMA
- WC SEGMA_001: GT='187'
    -> [answered|scorer=True] 187 amino acids
- PP SEGMA_001: GT='187'
    -> [answered|scorer=True] 187 amino acids

## SENTIEON_CLI
- WC SENTIEON_CLI_001: GT='CONSERVATIVE'
    -> [answered|scorer=True] CONSERVATIVE
- PP SENTIEON_CLI_001: GT='CONSERVATIVE'
    -> [answered|scorer=True] CONSERVATIVE

## TABPFN
- WC TABPFN_001: GT='~0.97 accuracy / ~0.99 ROC AUC; beats RF, LogReg, '
    -> [blocked|scorer=False] EXECUTION_REQUIRED — TabPFN requires a one-time interactive license ac
- WC TABPFN_002: GT='~0.84 R^2 / ~0.45 RMSE; beats LinReg and RandomFor'
    -> [answered|scorer=False] TabPFN (v2, CPU, 2 estimators, ignore_pretraining_limits) — MSE 0.1622
- PP TABPFN_001: GT='~0.97 accuracy / ~0.99 ROC AUC; beats RF, LogReg, '
    -> [blocked|scorer=False] EXECUTION_REQUIRED — TabPFN requires a one-time license acceptance / A
- PP TABPFN_002: GT='~0.84 R^2 / ~0.45 RMSE; beats LinReg and RandomFor'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — experiment could not be completed due to Python e

## USHER
- WC USHER_002: GT='64603'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — required dataset/model files (xenium_scGPT.h5ad, 
- PP USHER_001: GT='64603'
    -> [blocked|scorer=False] EXECUTION_REQUIRED — the specified Xenium/scRNA-seq .h5ad files and th