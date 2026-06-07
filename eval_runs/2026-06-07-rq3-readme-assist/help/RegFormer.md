# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute.

## RegFormer tasks
- The drug-response CSV question is a direct read of `random_test.csv` (no header; columns
  Loss/PCC/Spearman over 2 runs).
- **Cell-embedding question:** if `embeddings.npy` isn't at the quoted path, it is PRODUCED
  by the RegFormer cell-embedding pipeline — see `Docs/cell_emb.ipynb`,
  `downstream_task/regformer_emb.py`, and `Docs/configs/cell_emb_human_lung.toml`. Generate
  the embeddings by running that pipeline rather than giving up. The "dimensionality" answer
  is the number of columns (feature dim) of the embeddings array.
