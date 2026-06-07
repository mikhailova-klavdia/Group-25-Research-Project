# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## CyteOnto tasks
- The label CSVs live under `CyteOnto/notebooks/adv_tutorial/data/` (`author_labels.csv`,
  `algorithm1_labels.csv`, `algorithm2_labels.csv`); each has a `label` column. If a file
  isn't at the exact quoted path, search the repo / the adv_tutorial data dir before giving
  up — earlier runs wrongly declared `author_labels.csv` missing while the other label files
  were readable.
- "How many unique labels" = number of DISTINCT values in the `label` column (a small count).
- "First label" / "last label" = the first / last entry as stored in the CSV.
