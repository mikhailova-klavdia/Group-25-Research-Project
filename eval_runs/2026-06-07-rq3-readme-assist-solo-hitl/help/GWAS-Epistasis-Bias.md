# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## GWAS-Epistasis-Bias tasks
- The simulation/heatmap code is in the repo. The questions require ACTUALLY RUNNING the
  OLS-based GWAS simulation / generating the heatmap with the exact parameters given — an
  earlier run planned the modified simulation but never executed it and got blocked. Execute
  it and read the real output.
- Use the exact lambda range / SNP counts / thresholds from the question verbatim.
- Make sure the simulation actually COMPLETES (exit code 0) before reporting — a prior run's
  script crashed (a duplicated `workspace/workspace/` path) and a number was guessed instead of
  computed. Run from the workspace root, fix any path doubling, and read the real result.
