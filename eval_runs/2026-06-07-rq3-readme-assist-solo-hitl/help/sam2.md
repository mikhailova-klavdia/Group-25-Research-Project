# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## SAM2 tasks
- **Checkpoints are ALREADY in the repo — do NOT download.** They're under `checkpoints/`:
  `sam2.1_hiera_large.pt` and `sam2.1_hiera_tiny.pt`. An earlier run gave up trying to
  download the large checkpoint although it's present. Build the predictor from the LOCAL
  checkpoint plus its matching config under `configs/sam2.1/` (the config must match the
  checkpoint size — tiny vs large).
- **Dependencies:** needs `torch`, `hydra-core` (and `pillow`/`numpy`). Install them; if
  torch is heavy, be patient rather than reporting blocked.
- **Use the AUTOMATIC mask generator over the WHOLE image** (`SAM2AutomaticMaskGenerator`),
  with its DEFAULT settings — this is the "generate masks on the image" task. Two prior
  failure modes to avoid: (a) single-point/box prompting instead of the automatic generator
  yields only a couple of masks; (b) overriding the grid/threshold parameters yields hundreds.
  Stick to the automatic generator with defaults and count the masks it returns (order of tens).
- Fetch the image from the given URL first.
