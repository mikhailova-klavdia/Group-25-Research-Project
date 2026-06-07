# Agent hints for this paper — READ FIRST

These are **tips to steer you**, gathered from earlier attempts at these tasks. They are NOT the answer and NOT a full recipe — you must still do the real work with your tools and read the actual output. Use only what's relevant to the specific question you were given.

General reminders that tripped up earlier runs:
- Before declaring a file/weight "missing" or that something must be downloaded, search the whole repo (and staged workspace) — required models/data are often already present under a sub-path or produced by a tutorial in the repo.
- If a dependency fails to import after install, check for a NumPy 1.x vs 2.x clash (torch built against NumPy 1.x): `pip install 'numpy<2'` and re-run.
- Ground every numeric answer in a real successful execution; sanity-check the magnitude of what you compute.

## sentieon-cli tasks
- Run `dnascope` with `dry_run` enabled using the exact inputs given, then read the requested
  field (the calling mode it reports) from the dry-run output. NOTE: dry_run prints the
  planned command; it does NOT require the reference/model/dbSNP/BED files to actually be
  present, so don't block just because an input path is missing.
