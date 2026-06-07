# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## ScisTreeCNA tasks
- The test data (`test_data_reads.csv`, 100 SNP x 60 cells in `ref|alt|cn` format, and
  `test_data_tree.pkl`) belongs to the `scistreecna_basic` tutorial. If it isn't at the
  quoted path, generate it via the repo's basic tutorial/simulation before giving up.
- Run the repo's actual inference function (SciStree2 / ScisTreeCNA) with the exact
  parameters in the question. A prior run was close but slightly off — match the repo's
  inference routine and its native rounding; report the accuracy exactly as the code computes
  it (don't re-round yourself).
- If a step wants CuPy/GPU, use the CPU / NumPy code path.
