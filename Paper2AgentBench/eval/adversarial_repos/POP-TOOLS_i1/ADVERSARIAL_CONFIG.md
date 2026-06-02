# POP-TOOLS Adversarial Configurations

| Repo | Adversarial Configuration | Files Modified | Description |
|------|--------------------------|----------------|-------------|
| POP-TOOLS_i1 | (1) Missing dependencies | `requirements.txt`, `environment.yml` | See details below |
| POP-TOOLS_i2 | Known Python 2-to-3 issues | `ldsc/ldsc.py`, `ldsc/ldscore/regressions.py`, `ldsc/ldscore/sumstats.py` | See details below |
| POP-TOOLS_i3 | Typo errors | `compute.py`, `POP-GWAS.py` | See details below |
| POP-TOOLS_i4 | Wrong file paths | `test/test.sh`, `wiki/1.-POP‐GWAS.md`, `wiki/2.-POP‐GWAS-for-Rare‐Variant-Association-Studies.md` | See details below |

## POP-TOOLS_i1 — Missing Dependencies

Removed 3 required packages from `requirements.txt` and `environment.yml`:

| # | Removed Dependency | Expected Error | Used By |
|---|-------------------|----------------|---------|
| 1 | `numpy>=1.26.2` | `ModuleNotFoundError` | Core numerical operations in `compute.py`, `ldsc/ldscore/jackknife.py`, `ldsc/ldscore/ldscore.py`, `ldsc/ldscore/regressions.py`, etc. |
| 2 | `pandas>=2.1.4` | `ModuleNotFoundError` | DataFrame operations in `ldsc/munge_sumstats.py`, `ldsc/ldscore/sumstats.py`, `ldsc/ldscore/parse.py`, `ldsc/ldscore/regressions.py` |
| 3 | `scipy>=1.11.4` | `ModuleNotFoundError` | Statistical functions in `compute.py` (`chdtrc`), `ldsc/ldscore/regressions.py` (`norm`, `chi2`, `tdist`), `ldsc/ldscore/jackknife.py` (`nnls`) |

## POP-TOOLS_i2 — Known Python 2-to-3 Compatibility Issues

These are real bugs present in the original codebase (prior to our fixes), not manually injected errors. The repo is reset to commit `e5e3c92` (before the 3 fix commits).

| # | File | Line | Issue | Buggy Code | Fixed Code | Expected Error |
|---|------|------|-------|-----------|------------|----------------|
| 1 | `ldsc/ldsc.py` | 656 | `traceback.format_exc()` no longer accepts a positional argument in Python 3 | `traceback.format_exc(ex)` | `traceback.format_exc()` | `TypeError` |
| 2 | `ldsc/ldscore/sumstats.py` | 423 | Same `traceback.format_exc()` issue | `traceback.format_exc(ex)` | `traceback.format_exc()` | `TypeError` |
| 3 | `ldsc/ldscore/regressions.py` | 707–709 | `float()` on 0-d numpy arrays deprecated/broken in newer numpy | `float(rg.jknife_est)`, `float(rg.jknife_se)`, `float(rg_ratio)` | `np.asarray(...).item()` | `TypeError` or `DeprecationWarning` |

## POP-TOOLS_i3 — Typo Errors

Injected 2 misspelled names into Python import statements:

| # | File | Line | Original | Typo | Expected Error |
|---|------|------|----------|------|----------------|
| 1 | `compute.py` | 2 | `from scipy.special import chdtrc` | `from scipy.special import chdrtc` | `ImportError` — misspelled function name |
| 2 | `POP-GWAS.py` | 3 | `from compute import estimate_popgwas` | `from compute import estimate_popgwass` | `ImportError` — misspelled function name |

## POP-TOOLS_i4 — Wrong File Paths

Modified hardcoded paths to reference nonexistent locations:

| # | File | Line | Original | Changed To | Expected Error |
|---|------|------|----------|-----------|----------------|
| 1 | `test/test.sh` | all | `./test/data/` | `./test/input/` | `FileNotFoundError` — test data directory doesn't exist |
| 2 | `wiki/1.-POP‐GWAS.md` | all | `./test/data/` | `./test/input/` | Misleading documentation — wrong paths in examples |
| 3 | `wiki/2.-POP‐GWAS-for-Rare‐Variant-Association-Studies.md` | all | `./test/data/` | `./test/input/` | Misleading documentation — wrong paths in examples |
