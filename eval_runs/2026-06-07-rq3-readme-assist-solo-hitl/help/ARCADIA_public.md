# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## ARCADIA tasks
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
