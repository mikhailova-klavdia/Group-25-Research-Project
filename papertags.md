# Paper Tagging Scheme

## Folder Format

```
<rank>-<papernum><E/M/H>[tags]-<name>
```

Example: `32-64Mgd-augment-finetune-genomics`
- rank `32` → run 32nd (lower = more doable)
- paper `64`
- difficulty `M` (Medium)
- tags `gd` → needs GPU + data download
- name `augment-finetune-genomics`

---

## Difficulty

| Letter | Meaning |
|--------|---------|
| `E` | Easy — setup instructions are clear |
| `M` | Medium — installable but some ambiguity |
| `H` | Hard — agent cannot automate, needs human |

---

## Issue Tags

| Tag | Issue | Effect on pipeline |
|-----|-------|-------------------|
| `r` | R language repo | Env agent (Python/uv only) fails at step 1 |
| `c` | Compiled / conda-only / bioconda | uv cannot install it |
| `n` | No tutorials or notebooks found | Pipeline stalls after env setup, nothing to extract |
| `g` | GPU required | Tutorial execution crashes without CUDA |
| `d` | Data download needed | Tutorial crashes on missing files |
| `a` | API key needed at runtime | Calls fail without key |
| `w` | Pretrained weights needed | Model fails to load |
| `k` | Docker / container only | Nothing runs outside container |

Tags combine: `wgd` = weights + GPU + data all needed.

---

## Tiers

| Ranks | Tier | Description |
|-------|------|-------------|
| 01–21 | Fully automatic | Clean Python + PyPI + has tutorials — run unattended |
| 22–34 | One runtime blocker | Python env works, single tag blocks execution |
| 35–50 | Wrong language/tool | Clear setup but `r` or `c` — env agent can't handle |
| 51–66 | No tutorials / unclear | Env may work but nothing to extract |
| 67–74 | Hard | Multiple blockers, needs human intervention |

---

## Full Index

| Rank | Folder | Notes |
|------|--------|-------|
| 01 | 01-3M-CyteOnto | |
| 02 | 02-5M-GWAS-Epistasis-Bias | |
| 03 | 03-9M-USHER | |
| 04 | 04-10M-blobtk | |
| 05 | 05-12M-genecad | |
| 06 | 06-13M-gffutilsAI | |
| 07 | 07-14M-ionstats | |
| 08 | 08-18M-ovo | |
| 09 | 09-20M-sentieon-cli | |
| 10 | 10-21M-svirlpool | |
| 11 | 11-27M-GWProt | |
| 12 | 12-31M-InCytokine | |
| 13 | 13-34M-LARIS | |
| 14 | 14-36M-PathWeigh | |
| 15 | 15-37M-SC-Framework | |
| 16 | 16-38M-SEGMA | |
| 17 | 17-39M-ScisTreeCNA | |
| 18 | 18-54M-distortions | |
| 19 | 19-57M-ARCADIA_public | |
| 20 | 20-62M-RegFormer | |
| 21 | 21-66M-fadvi | |
| 22 | 22-17Md-mm2-ivh | needs data download |
| 23 | 23-53Ma-SRAgent | needs API key |
| 24 | 24-63Mw-Zygosity_DNALM | needs pretrained weights |
| 25 | 25-48Mg-scRegulate | needs GPU |
| 26 | 26-44Md-medchem | unclear external deps |
| 27 | 27-28Mc-GeneScanner | conda-only channels |
| 28 | 28-26Mg-ECLIPSE | needs GPU |
| 29 | 29-59Mg-HypergraphEmbedding4MetabolicNetworks | needs GPU |
| 30 | 30-67Mg-ML_evolution_SARS-CoV-2 | needs GPU |
| 31 | 31-68Mg-CrossPPI | needs GPU |
| 32 | 32-64Mgd-augment-finetune-genomics | needs GPU + data |
| 33 | 33-65Mwg-cpiVAE_v1 | needs weights + GPU |
| 34 | 34-2Mn-ChainStorm | no tutorials found |
| 35 | 35-4Ec-DipGenie | compiled/Makefile |
| 36 | 36-11Ec-breakinator | Rust/bioconda |
| 37 | 37-15Ec-kcftools | bioconda |
| 38 | 38-51Ec-RECODE | bioconda |
| 39 | 39-52Ec-SAGA | bioconda |
| 40 | 40-56Ec-singletrack | bioconda |
| 41 | 41-6Er-MethylSeqR | R package |
| 42 | 42-41Er-StratifiedShapes | R package |
| 43 | 43-42Er-TSProm | R package |
| 44 | 44-55Er-scRNA-seq-genetic-ancestry | R/Bioconductor |
| 45 | 45-60Er-StandardCor | R package |
| 46 | 46-1Mr-CBKMR | R package |
| 47 | 47-16Mr-metaboprep | R package |
| 48 | 48-23Mr-ASVNet | R package |
| 49 | 49-25Mr-ConsensusMetaDA | R package |
| 50 | 50-40Mr-SpaceBF | R package |
| 51 | 51-7Mn-PathogenSurveillance | no tutorials |
| 52 | 52-8Mn-SaVor | no tutorials |
| 53 | 53-19Mnd-reference_set_selection_benchmark | no tutorials + data needed |
| 54 | 54-22Mnd-16S_DB | no tutorials + data needed |
| 55 | 55-24Mn-BioPrediction-PPI | no tutorials |
| 56 | 56-29Mn-HepatocyteDamageScore | no tutorials |
| 57 | 57-30Mn-IBIS-rSNP | no tutorials |
| 58 | 58-32Mn-Integrative-RNA-Seq-sRNA | no tutorials |
| 59 | 59-33Mn-TNBC | no tutorials |
| 60 | 60-35Mn-MANU_copangraph | no tutorials |
| 61 | 61-43Mn-aging-gtex-xci | no tutorials |
| 62 | 62-46Mn-pmultiqc | no tutorials |
| 63 | 63-61Mn-IDEA_DNA_Methylation | no tutorials |
| 64 | 64-69Mn-FP_2025 | no tutorials |
| 65 | 65-71Mn-rna-harmonization-ai | no tutorials |
| 66 | 66-45Mk-metapointfinder | Docker only |
| 67 | 67-72Ha-SKiM-GPT | needs API key |
| 68 | 68-47Hdk-scDock | data + Docker |
| 69 | 69-50Hc-PyrMol | conda-only, no pip |
| 70 | 70-58Hkd-FoldConfBench | Docker + data |
| 71 | 71-49Hwg-tissuenarrator | weights + GPU (48GB VRAM) |
| 72 | 72-70Hwg-cryosiam | weights + GPU |
| 73 | 73-74Hwgd-Evo2HiC | weights + GPU + data |
| 74 | 74-73Hwgd-PPLM | weights + GPU + data + external tools |
