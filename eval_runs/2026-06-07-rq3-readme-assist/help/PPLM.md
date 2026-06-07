# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute.

## PPLM tasks
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
