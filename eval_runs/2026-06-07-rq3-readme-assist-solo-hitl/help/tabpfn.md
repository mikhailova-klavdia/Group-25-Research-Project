# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- If an import is missing, INSTALL it yourself (`pip install <pkg>`) and re-run — do not give up assuming something else will install it. Most things also run fine on CPU; don't abandon a task claiming a GPU is required without trying CPU first.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute, and never report a number you did not actually compute.

## TabPFN tasks
- **You do NOT need a TABPFN_TOKEN.** The license/token gate only applies to the GATED model
  versions (v2.5 / v2.6). A bare `TabPFNClassifier()` / `TabPFNRegressor()` defaults to the
  latest gated model — that's the trap an earlier run hit ("requires license acceptance").
- **The non-gated v2 weights are cached locally** at `~/Library/Caches/tabpfn/`
  (`tabpfn-v2-classifier-finetuned-zk73skhh.ckpt` and `tabpfn-v2-regressor.ckpt`). Construct
  the model with `model_path=` pointing to the cached file (a path string loads from disk and
  skips the download/gate), `device='cpu'`. Equivalent:
  `create_default_for_version(ModelVersion.V2, device='cpu')`.
- If you cross-validate, build a FRESH TabPFN estimator inside each fold — do NOT
  `sklearn.clone()` it (clone can drop `model_path` and re-trigger the gate).
- Compare against standard sklearn baselines (LogReg/RandomForest/SVC for classification;
  LinearRegression/RandomForest for regression) and report the metrics you actually compute.
