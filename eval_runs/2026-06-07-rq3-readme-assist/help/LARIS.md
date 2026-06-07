# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute.

## LARIS tasks
- These use the tutorial AnnData `adata_tonsil.h5ad` (human tonsil Slide-tags, ~5695 cells)
  and the ligand-receptor DB, both part of the `04_laris_tutorial`. Earlier runs gave up
  saying the `.h5ad` was missing — before doing so, search the whole repo and staged
  workspace (e.g. under `tests/data/` and the tutorial's `data/.../LARIS_tutorial_datasets/`)
  and check whether the tutorial/test fixtures provide or download it. The LR database CSVs
  are under `laris/datasets/_data/`.
- The answers come from running the LARIS pipeline on that data (a cell/edge count and a top
  gene name). Don't stop at "file not found" without exhausting the repo.
