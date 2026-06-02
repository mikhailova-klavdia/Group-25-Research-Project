# AlphaGenome Adversarial Configurations

| Repo | Adversarial Configuration | Files Modified | Description |
|------|--------------------------|----------------|-------------|
| AlphaGenome_i1 | (4) Deprecated API replacements | `colabs/batch_variant_scoring.ipynb`, `colabs/quick_start.ipynb` | See details below |

## AlphaGenome_i1 — Deprecated API Replacements

| # | File | Cell | Original | Deprecated Replacement | Expected Error |
|---|------|------|----------|----------------------|----------------|
| 1 | `colabs/batch_variant_scoring.ipynb` | cell-5 | `pd.read_csv(StringIO(vcf_file), sep='\t')` | `pd.DataFrame.from_csv(StringIO(vcf_file), sep='\t')` | `AttributeError` — `from_csv` removed in pandas 1.0 |
| 2 | `colabs/quick_start.ipynb` | cell-29 | `pd.read_feather(url)` | `import feather; feather.read_dataframe(url)` | `ModuleNotFoundError` — `feather-format` package deprecated in favor of `pyarrow.feather` |
| 3 | `colabs/quick_start.ipynb` | cell-43 | (no `plt.hold` call) | Added `plt.hold(True)` before plotting | `AttributeError` — `plt.hold` removed in matplotlib 3.0 |
| Repo | Adversarial Configuration | Files Modified | Description |
|------|--------------------------|----------------|-------------|
| AlphaGenome_i2 | (1) Missing dependencies | `pyproject.toml` | See details below |
| AlphaGenome_i3 | (3) Cell-level typo errors | `colabs/batch_variant_scoring.ipynb`, `colabs/quick_start.ipynb` | See details below |
| AlphaGenome_i4 | (2) Wrong file paths | `colabs/batch_variant_scoring.ipynb`, `data/4_variants.tsv` | See details below |

## AlphaGenome_i4 — Wrong File Paths

The variant data was extracted from the inline string into an external file (`data/4_variants.tsv`), but the notebook references a nonexistent path.

| # | File | Cell | Issue | Path Used | Correct Path | Expected Error |
|---|------|------|-------|-----------|--------------|----------------|
| 1 | `colabs/batch_variant_scoring.ipynb` | cell-5 | Wrong filename in path | `../data/variants.tsv` | `../data/4_variants.tsv` | `FileNotFoundError` |

## AlphaGenome_i3 — Cell-Level Typo Errors

| # | File | Cell | Typo | Original | Expected Error |
|---|------|------|------|----------|----------------|
| 1 | `colabs/batch_variant_scoring.ipynb` | cell-5 | Misspelled attribute | `variant.referece_interval` (should be `reference_interval`) | `AttributeError` |
| 2 | `colabs/quick_start.ipynb` | cell-29 | Misspelled method name | `gene_annotation.filter_protien_coding(gtf)` (should be `filter_protein_coding`) | `AttributeError` |
| 3 | `colabs/quick_start.ipynb` | cell-13 | Extra closing parenthesis | `))` at end of statement | `SyntaxError` |

## AlphaGenome_i2 — Missing Dependencies

Removed 6 required packages from `pyproject.toml` `[project] dependencies`:

| # | Removed Dependency | Expected Error | Used By |
|---|-------------------|----------------|---------|
| 1 | `numpy` | `ModuleNotFoundError` | Core numerical operations throughout |
| 2 | `pandas` | `ModuleNotFoundError` | DataFrame operations in notebooks and variant scoring |
| 3 | `protobuf>=5.28.3` | `ModuleNotFoundError` | gRPC protocol buffer serialization |
| 4 | `pyarrow` | `ModuleNotFoundError` | `pd.read_feather()` in quick_start.ipynb |
| 5 | `scipy` | `ModuleNotFoundError` | Scientific computing utilities |
| 6 | `seaborn` | `ModuleNotFoundError` | Statistical visualization |
