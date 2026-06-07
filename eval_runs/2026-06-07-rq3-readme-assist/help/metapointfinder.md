# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute.

## metapointfinder tasks
- The tools (mutant generator, `generate_dna_mutants`, `pad_sequences`) are in the repo
  (see `benchmark/` and the package modules). Inputs sit under
  `metapointfinder/notebooks/<tool>/.../input|data/`.
- The two mutant-generation questions (TSV+FASTA) are solvable directly with the provided
  inputs — count the generated wildtype+mutant sequences as the question defines.
- **pad_sequences questions:** the tool pads/truncates each FASTA record to the target length
  the question gives. If the input FASTA isn't at the quoted path, check the repo for a
  sample or create the minimal input the tool expects, then run the pad tool
  (`benchmark/pad_to_10kb.py` or the `pad_sequences` tool) with the specified target length
  and read the resulting length/count from the real output.
