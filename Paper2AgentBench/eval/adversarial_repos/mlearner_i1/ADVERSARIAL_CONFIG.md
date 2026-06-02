# Adversarial Configurations for mlearner_i1–i4

## Summary

| Config | Category | Files Modified | # Issues |
|--------|----------|---------------|----------|
| mlearner_i1 | Missing Dependencies | `README.md` | 3 |
| mlearner_i2 | Language/Compatibility Issues | `M_Learner_I.R` | 2 |
| mlearner_i3 | Typo Errors | `M_Learner_I.R` | 2 |
| mlearner_i4 | Wrong File Paths | `README.md` | 1 (all occurrences) |

---

## mlearner_i1 — Missing Dependencies

Removed 3 packages from the `install.packages()` line in `README.md` (line 52) so users won't install them. The `require()` calls in `M_Learner_I.R` remain, so the script fails at runtime.

| # | Removed Dependency | Expected Error | Used By |
|---|-------------------|----------------|---------|
| 1 | `sandwich` | `Error in library(sandwich)` | `get_vcov()` — robust covariance (line 182) |
| 2 | `lmtest` | `Error in library(lmtest)` | `coeftest()` in BLP/SATES (lines 208, 260) |
| 3 | `data.table` | `Error in library(data.table)` | `fread()` for loading input data (lines 589–591) |

---

## mlearner_i2 — R Compatibility Issues

Replaced `fread()` with `read.table()` in `M_Learner_I.R`. `read.table` defaults to `header=FALSE`, misreading the header row as data and causing dimension mismatch or numeric conversion errors.

| # | Line | Original | Changed To | Expected Error |
|---|------|----------|-----------|----------------|
| 1 | 589 | `Y <- as.matrix(fread(Y_file))` | `Y <- as.matrix(read.table(Y_file))` | Header row read as data; dimension mismatch or non-numeric conversion |
| 2 | 590 | `D <- as.matrix(fread(D_file))` | `D <- as.matrix(read.table(D_file))` | Same — treatment vector includes header as a row |

---

## mlearner_i3 — Typo Errors

Misspelled package names in `require()` calls in `M_Learner_I.R`.

| # | Line | Original | Typo | Expected Error |
|---|------|----------|------|----------------|
| 1 | 7 | `require(mlr3)` | `require(mlr4)` | Package 'mlr4' not found |
| 2 | 9 | `require(sandwich)` | `require(sandwitch)` | Package 'sandwitch' not found |

---

## mlearner_i4 — Wrong File Paths

Changed all occurrences of `example_data/` to `example/` in `README.md`. The `example/` directory doesn't exist, so users following the README examples will get file-not-found errors.

| # | Lines | Original | Changed To | Expected Error |
|---|-------|----------|-----------|----------------|
| 1 | 30–32 | `example_data/` | `example/` | File not found — directory doesn't exist |
