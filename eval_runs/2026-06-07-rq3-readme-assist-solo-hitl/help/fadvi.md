# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## fadvi tasks
- **Batch-latent-dim question:** the pretrained model lives in
  `fadvi/notebooks/basic_usage/fadvi_save/`. Load the saved FADVI model and read the batch
  latent representation's feature count from it. If that save dir is empty, the basic_usage
  tutorial trains the model — run it first rather than giving up.
- **AnnData-from-CSV question:** build the AnnData from the provided expression/metadata CSVs
  and select highly-variable genes as the question specifies; the answer is a small count.
- **spatial+single-cell question:** needs the scRNA/spatial `.h5ad`; search the repo / run
  the relevant tutorial to obtain them before declaring them missing.
