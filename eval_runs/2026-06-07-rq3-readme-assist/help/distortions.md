# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute.

## distortions tasks
- The C. elegans data (`c_elegans_metadata.csv`, `c_elegans_data.csv`) and the PBMC3k
  AnnData are loaded by the repo tutorials (`docs/tutorials/c_elegans.ipynb`). If the files
  aren't at the quoted path, the tutorial fetches/creates them — run the data-loading cells
  rather than giving up (earlier runs stopped at "file not found" although the data is
  obtainable from the tutorial).
- "How many unique cell types" = DISTINCT values in the `cell.type` column.
- **UMAP-neighbors count question:** a prior run was off by one. Re-check exactly what you're
  counting (e.g. whether the point itself is included, or a 0- vs 1-based grouping); recompute
  carefully.
