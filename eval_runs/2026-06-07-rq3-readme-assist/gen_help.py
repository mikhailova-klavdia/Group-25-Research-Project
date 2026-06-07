#!/usr/bin/env python
"""Generate the 18 per-paper help READMEs (AGENT_HINTS) from the analysis.

Each file is hints/steering ONLY — never the ground-truth answer and never a full
step-by-step recipe. Heaviest guidance goes to the questions the two best autonomous
teams (worker-critic, worker-critic-plus-plus) got WRONG or gave up on, derived from
their chains + AUDIT.md + the current on-disk data/weight locations.
"""
from pathlib import Path

HEADER = (
    "# Agent hints for this paper — READ FIRST\n\n"
    "These are **tips to steer you**, gathered from earlier attempts at these tasks. "
    "They are NOT the answer and NOT a full recipe — you must still do the real work "
    "with your tools and read the actual output. Use only what's relevant to the "
    "specific question you were given.\n\n"
    "General reminders that tripped up earlier runs:\n"
    "- Before declaring a file/weight \"missing\" or that something must be downloaded, "
    "search the whole repo (and staged workspace) — required models/data are often "
    "already present under a sub-path or produced by a tutorial in the repo.\n"
    "- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash "
    "(torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.\n"
    "- Ground every numeric answer in a real successful execution; sanity-check the "
    "magnitude of what you compute.\n\n"
)

HELP = {

"ARCADIA_public": """## ARCADIA tasks
- **Config-value question (run_pipeline / config.json):** the value is read straight from
  `ARCADIA_public/repo/ARCADIA_public/configs/config.json`. Read the right field.
- **Hyperparameter-search grid-count question:** this asks for the *number of parameter
  combinations* in the search grid, NOT a value from the config and NOT the result of
  running training. A prior run answered a large config-derived number (≈162) — that is the
  wrong interpretation. Read `scripts/hyperparameter_search.py` to see how the grid is
  built (it's an `itertools.product` over the option lists). The count is simply the
  PRODUCT of the lengths of the option lists the question specifies (the n_layers options
  times the latent_dim options). Compute that product; it is a small number. Do not run the
  full search.
""",

"CrossPPI": """## CrossPPI tasks
- **Dependencies:** CrossPPI needs `torch` and ESM (`fair-esm`, imported as `esm`). Earlier
  runs gave up because these weren't installed — install them (be patient; torch is large)
  rather than reporting EXECUTION_REQUIRED.
- **Predictor / scripts:** the inference entry points are `t.py` / `main_cv.py`; embeddings
  are produced by `embedding.py`. Use the PRE-TRAINED models in the save directory — do not
  retrain.
- **pKD questions:** run the ensemble predictor with the pre-trained models; the answer is a
  single positive pKD on the usual binding scale. A near-correct earlier run shows this is
  achievable once torch/esm are installed — don't give up on the install.
- **ESM embedding ROW-COUNT question:** the number of rows must equal the input sequence
  length. The raw ESM-2 output has TWO extra rows — a leading BOS and a trailing EOS special
  token. Earlier runs returned length+2; strip those two special tokens (e.g.
  `embeddings[1:-1]`) so rows == sequence length.
- **"Mean of the FIRST residue embedding vector" question:** earlier runs returned ≈0, which
  is the mean of an ordinary interior residue vector — that is the wrong row. Reconsider what
  "the first vector" of the raw model output is; the leading token's statistics differ
  markedly from interior residues. Sanity-check: the expected magnitude is well away from 0.
""",

"CyteOnto": """## CyteOnto tasks
- The label CSVs live under `CyteOnto/notebooks/adv_tutorial/data/` (`author_labels.csv`,
  `algorithm1_labels.csv`, `algorithm2_labels.csv`); each has a `label` column. If a file
  isn't at the exact quoted path, search the repo / the adv_tutorial data dir before giving
  up — earlier runs wrongly declared `author_labels.csv` missing while the other label files
  were readable.
- "How many unique labels" = number of DISTINCT values in the `label` column (a small count).
- "First label" / "last label" = the first / last entry as stored in the CSV.
""",

"GWAS-Epistasis-Bias": """## GWAS-Epistasis-Bias tasks
- The simulation/heatmap code is in the repo. The questions require ACTUALLY RUNNING the
  OLS-based GWAS simulation / generating the heatmap with the exact parameters given — an
  earlier run planned the modified simulation but never executed it and got blocked. Execute
  it and read the real output.
- Use the exact lambda range / SNP counts / thresholds from the question verbatim.
""",

"GWProt": """## GWProt tasks
- Straightforward reads/executions. Load the PDB files from the quoted `Example_Data/KRAS
  Proteins/` directory to build the protein objects and count them; for ligand types, count
  the DISTINCT ligand categories in the `KRAS Ligands.csv` metadata. Mind the space in the
  directory/file names.
""",

"LARIS": """## LARIS tasks
- These use the tutorial AnnData `adata_tonsil.h5ad` (human tonsil Slide-tags, ~5695 cells)
  and the ligand-receptor DB, both part of the `04_laris_tutorial`. Earlier runs gave up
  saying the `.h5ad` was missing — before doing so, search the whole repo and staged
  workspace (e.g. under `tests/data/` and the tutorial's `data/.../LARIS_tutorial_datasets/`)
  and check whether the tutorial/test fixtures provide or download it. The LR database CSVs
  are under `laris/datasets/_data/`.
- The answers come from running the LARIS pipeline on that data (a cell/edge count and a top
  gene name). Don't stop at "file not found" without exhausting the repo.
""",

"PPLM": """## PPLM tasks
- **Weights are ALREADY in the repo — do not download.** The pretrained model is at
  `weights/pplm_t33_650M.pt` (also `pplm/models/pplm_t33_650M.pt`); the affinity models are
  at `weights/affinity_models.pkl`. Stage and use them. An earlier run wrongly reported the
  model file as absent.
- **NumPy clash (this blocks PPLM):** the repo's torch is built against NumPy 1.x. If you see
  "A module compiled using NumPy 1.x cannot be run in NumPy 2.0", run `pip install 'numpy<2'`
  (force-reinstall if needed) and re-run. Earlier successful runs all needed this.
- **Use the provided 650M model, not a smaller ESM-2 variant.** A prior run substituted a
  smaller ESM-2 model and got the wrong (too-small) per-residue embedding width. The repo
  ships the correct model at `pplm_t33_650M.pt` — use it so the embedding shape matches the
  paper's model (don't swap in a lighter ESM-2 checkpoint).
- **Affinity questions** (`run_pplm-affinity.py`): use the receptor.fasta + ligand.fasta and
  `weights/affinity_models.pkl`. A prior run took a different code path and got a wrong
  binding energy — use the repo's affinity script with the example FASTAs.
- **Embedding / shape / PPI-probability questions** (`run_pplm.py`): use seq1.fasta /
  seq2.fasta with the 650M weights. If you actually executed the PPI tool, report the real
  probability — don't over-flag a genuinely executed result as ungrounded.
""",

"RegFormer": """## RegFormer tasks
- The drug-response CSV question is a direct read of `random_test.csv` (no header; columns
  Loss/PCC/Spearman over 2 runs).
- **Cell-embedding question:** if `embeddings.npy` isn't at the quoted path, it is PRODUCED
  by the RegFormer cell-embedding pipeline — see `Docs/cell_emb.ipynb`,
  `downstream_task/regformer_emb.py`, and `Docs/configs/cell_emb_human_lung.toml`. Generate
  the embeddings by running that pipeline rather than giving up. The "dimensionality" answer
  is the number of columns (feature dim) of the embeddings array.
""",

"SC-Framework": """## SC-Framework tasks
- Direct read: load the AnnData `adata_rna.h5ad` and report the number of observations
  (`adata.n_obs`).
""",

"ScisTreeCNA": """## ScisTreeCNA tasks
- The test data (`test_data_reads.csv`, 100 SNP x 60 cells in `ref|alt|cn` format, and
  `test_data_tree.pkl`) belongs to the `scistreecna_basic` tutorial. If it isn't at the
  quoted path, generate it via the repo's basic tutorial/simulation before giving up.
- Run the repo's actual inference function (SciStree2 / ScisTreeCNA) with the exact
  parameters in the question. A prior run was close but slightly off — match the repo's
  inference routine and its native rounding; report the accuracy exactly as the code computes
  it (don't re-round yourself).
- If a step wants CuPy/GPU, use the CPU / NumPy code path.
""",

"USHER": """## USHER tasks
- This needs `xenium_scGPT.h5ad`, `scRNAseq_scGPT.h5ad`, and an alignment model under
  `USHER/repo/USHER/datasets/`. Search the entire repo for these before concluding they're
  absent, and check for any download/setup script the repo provides. If, after a thorough
  search, the data genuinely isn't present and there is no way to fetch it, the task cannot be
  completed honestly — but confirm that first.
""",

"distortions": """## distortions tasks
- The C. elegans data (`c_elegans_metadata.csv`, `c_elegans_data.csv`) and the PBMC3k
  AnnData are loaded by the repo tutorials (`docs/tutorials/c_elegans.ipynb`). If the files
  aren't at the quoted path, the tutorial fetches/creates them — run the data-loading cells
  rather than giving up (earlier runs stopped at "file not found" although the data is
  obtainable from the tutorial).
- "How many unique cell types" = DISTINCT values in the `cell.type` column.
- **UMAP-neighbors count question:** a prior run was off by one. Re-check exactly what you're
  counting (e.g. whether the point itself is included, or a 0- vs 1-based grouping); recompute
  carefully.
""",

"fadvi": """## fadvi tasks
- **Batch-latent-dim question:** the pretrained model lives in
  `fadvi/notebooks/basic_usage/fadvi_save/`. Load the saved FADVI model and read the batch
  latent representation's feature count from it. If that save dir is empty, the basic_usage
  tutorial trains the model — run it first rather than giving up.
- **AnnData-from-CSV question:** build the AnnData from the provided expression/metadata CSVs
  and select highly-variable genes as the question specifies; the answer is a small count.
- **spatial+single-cell question:** needs the scRNA/spatial `.h5ad`; search the repo / run
  the relevant tutorial to obtain them before declaring them missing.
""",

"metapointfinder": """## metapointfinder tasks
- The tools (mutant generator, `generate_dna_mutants`, `pad_sequences`) are in the repo
  (see `benchmark/` and the package modules). Inputs sit under
  `metapointfinder/notebooks/<tool>/.../input|data/`.
- The two mutant-generation questions (TSV+FASTA) are solvable directly with the provided
  inputs — count the generated wildtype+mutant sequences as the question defines.
- **pad_sequences questions:** the tool pads/truncates each FASTA record to the target length
  the question gives. If the input FASTA isn't at the quoted path, check the repo for a
  sample or create the minimal input the tool expects, then run the pad tool
  (`benchmark/pad_to_10kb.py` or the `pad_sequences` tool) with the specified target length
  and read the resulting length/count from the real output.
""",

"sam2": """## SAM2 tasks
- **Checkpoints are ALREADY in the repo — do NOT download.** They're under `checkpoints/`:
  `sam2.1_hiera_large.pt` and `sam2.1_hiera_tiny.pt`. An earlier run gave up trying to
  download the large checkpoint although it's present. Build the predictor from the LOCAL
  checkpoint plus its matching config under `configs/sam2.1/` (the config must match the
  checkpoint size — tiny vs large).
- **Dependencies:** needs `torch`, `hydra-core` (and `pillow`/`numpy`). Install them; if
  torch is heavy, be patient rather than reporting blocked.
- Fetch the image from the given URL, run the automatic mask generator, and report the number
  of masks (expect on the order of tens).
""",

"segma": """## SEGMA tasks
- Direct execution: run `process_sequences` on the input FASTA and sum the amino-acid counts
  across all sequences.
""",

"sentieon-cli": """## sentieon-cli tasks
- Run `dnascope` with `dry_run` enabled using the exact inputs given, then read the requested
  field (the calling mode it reports) from the dry-run output. NOTE: dry_run prints the
  planned command; it does NOT require the reference/model/dbSNP/BED files to actually be
  present, so don't block just because an input path is missing.
""",

"tabpfn": """## TabPFN tasks
- **You do NOT need a TABPFN_TOKEN.** The license/token gate only applies to the GATED model
  versions (v2.5 / v2.6). A bare `TabPFNClassifier()` / `TabPFNRegressor()` defaults to the
  latest gated model — that's the trap an earlier run hit ("requires license acceptance").
- **The non-gated v2 weights are cached locally** at `~/Library/Caches/tabpfn/`
  (`tabpfn-v2-classifier-finetuned-zk73skhh.ckpt` and `tabpfn-v2-regressor.ckpt`). Construct
  the model with `model_path=` pointing to the cached file (a path string loads from disk and
  skips the download/gate), `device='cpu'`. Equivalent:
  `create_default_for_version(ModelVersion.V2, device='cpu')`.
- If you cross-validate, build a FRESH TabPFN estimator inside each fold — do NOT
  `sklearn.clone()` it (clone can drop `model_path` and re-trigger the gate).
- Compare against standard sklearn baselines (LogReg/RandomForest/SVC for classification;
  LinearRegression/RandomForest for regression) and report the metrics you actually compute.
""",
}

OUT = Path(__file__).resolve().parent / "help"
OUT.mkdir(exist_ok=True)
for slug, body in HELP.items():
    (OUT / f"{slug}.md").write_text(HEADER + body, encoding="utf-8")
print(f"wrote {len(HELP)} help files to {OUT}")
for slug in sorted(HELP):
    print("  ", slug)
