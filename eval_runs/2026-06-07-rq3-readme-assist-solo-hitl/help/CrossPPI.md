# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## CrossPPI tasks
- **Dependencies:** CrossPPI needs `torch` and ESM (`fair-esm`, imported as `esm`). Earlier
  runs gave up because these weren't installed — install them (be patient; torch is large)
  rather than reporting EXECUTION_REQUIRED.
- **Predictor / scripts:** the inference entry points are `t.py` / `main_cv.py`; embeddings
  are produced by `embedding.py`. Use the PRE-TRAINED models in the save directory — do not
  retrain.
- **pKD questions:** run the ensemble predictor with the pre-trained models; the answer is a
  single positive pKD on the usual binding scale. A near-correct earlier run shows this is
  achievable once torch/esm are installed — don't give up on the install.
- **ESM embedding ROW-COUNT question:** the number of rows must equal the input sequence
  length. The raw ESM-2 output has TWO extra rows — a leading BOS and a trailing EOS special
  token. Earlier runs returned length+2; strip those two special tokens (e.g.
  `embeddings[1:-1]`) so rows == sequence length.
- **"Mean of the FIRST residue embedding vector" question:** earlier runs returned ≈0, which
  is the mean of an ordinary interior residue vector — that is the wrong row. Reconsider what
  "the first vector" of the raw model output is; the leading token's statistics differ
  markedly from interior residues. Sanity-check: the expected magnitude is well away from 0.
