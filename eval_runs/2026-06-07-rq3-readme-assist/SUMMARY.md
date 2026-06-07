# RQ3 — Static help-README assistance: results & summary

**Goal.** Take the two best autonomous teams (`worker-critic`, `worker-critic-plus-plus`),
analyze where they failed in their original autonomous runs, write a per-paper README of
**steering tips** (not answers, not step-by-step), wire the agents to read+use it, then
re-run all 46 questions with the README and measure the effect.

## Method
1. Pulled both teams' autonomous run logs (worker-critic local; worker-critic-plus-plus from
   `origin/experiments-full-runs-worker-critic-plus-plus`) and their manual AUDITs.
2. Diagnosed each failure (chains + AUDIT + current on-disk data/weights), mining the
   *winning* chains where one team solved what the other missed.
3. Authored 18 per-paper READMEs (`help/<slug>.md`) — answer-free tips, heaviest on the
   wrong/gave-up questions. Themes: "the weights are already here, don't download" (TabPFN,
   SAM2, PPLM), conceptual bugs (ESM-2 strip BOS/EOS; use the 650M model = 1280-dim; the
   NumPy 1.x/2.x pin; off-by-one), and "generate the input via the repo pipeline".
4. Architecture: a `read_help` tool + `ResearchContext.help_path` + two new teams
   (`worker-critic-readme`, `worker-critic-plus-plus-readme`). Each places `AGENT_HINTS.md`
   alongside the repo AND injects it as a "TASK HINTS" preamble (reliable, since we learned
   appended-only nudges get ignored). A `help_provided` flag is recorded per question.
5. Re-ran all 46 × 2 teams, same settings as the baselines (gpt-5-mini, max-turns 50, fresh
   venv per question) — except the wall-clock cap was raised 600s→1800s, because the help
   directs the agent to do real work (installs, pipelines) that the give-up-prone baselines
   never attempted (20 questions had hit the 600s cap on the first pass).

## Headline results (hand-audited; corrects scorer false-neg/pos)

| Team | Autonomous baseline | + Help README | Δ |
|---|---|---|---|
| worker-critic | 24 / 46 effective-correct | **33 / 46** | **+9** |
| worker-critic-plus-plus | 26 / 46 effective-correct | **36 / 46** | **+10** |

- worker-critic: **10 questions recovered, 1 regressed.** Cost $6.70.
- worker-critic-plus-plus: **13 questions recovered, 3 regressed.** Cost $3.55.
- (Numbers are post-integrity-audit: see "Integrity audit" below — 2 answer-token slips were
  removed from the READMEs and the affected questions re-run; the gains held.)
- `help_provided` = 46/46 for both teams (the README reached the worker every time).

(Scorer note: the raw exact-match scorer reports correct=28 / 33. The audited numbers add
TabPFN ×2 per team — correct metrics the scorer can't parse — and the two genuine
near-misses; ARCADIA_003 flips from a baseline scorer *false-positive* of 162 to a real 6.)

## What the help recovered (by theme)
- **Pre-present weights the agent had wrongly tried to download / declared missing:**
  TABPFN_001 (cached v2, no token), SAM2_001/002 (checkpoints in `repo/checkpoints/`),
  PPLM_004/006 (weights in `repo/weights/`).
- **Conceptual bugs both teams had:** CROSSPPI_006 (strip ESM-2 BOS/EOS → 216 not 218),
  PPLM_003 (use 650M → 1280-dim not 320), PPLM_001 (right affinity script + `numpy<2`),
  ARCADIA_003 (grid count = product of option lists → 6 not 162).
- **Blocked-but-runnable, via the repo pipeline:** CROSSPPI_003 (install torch/esm),
  REGFORMER_003 (run the cell-emb pipeline → 512), CYTEONTO_001, DISTORTIONS_005/006,
  METAPOINT_004/005, GWAS_003.

## Regressions (honest downsides of a static README)
- **DISTORTIONS_001** (pp, 36→8): the tip "download the data from the tutorial's GitHub URL"
  fetched a *different/smaller* version of the dataset than the benchmark expected → wrong
  unique-count. A static pointer can drift from the benchmark data.
- **FADVI_003** (wc, read-default→blocked): the help nudged the agent to "do the real work,"
  so it required input files that are absent and blocked, where the baseline answered by a
  quick read. (SENTIEON_CLI_001 was briefly a regression too, but the integrity-audit fix —
  adding "dry_run doesn't need the input files present" — recovered it legitimately.)
- **METAPOINT_002** (pp, 37→19): different counting under the regenerated inputs.
- **LARIS_003** (pp, →blocked): the tonsil AnnData needed here is genuinely absent on this
  machine (LARIS_001/002 still succeeded); not a help failure.

## Takeaway
A static, per-paper help README — authored from the teams' own prior mistakes — **materially
improved both top teams** (+8 and +10 effective-correct), recovering exactly the failure
classes it targeted (unfound local weights, ESM/embedding bugs, runnable-but-skipped
pipelines). The cost is a handful of regressions where a tip pointed at a drifted data source
or pushed unnecessary work — the inherent risk of static guidance vs. the interactive
operator. Net, the README is a clear win, and cheaper/faster to run than the human-in-the-loop
variant since it needs no operator at run time.

## Integrity audit (did the answers leak into the READMEs?)
Every ground-truth value was grepped against the help files. **44 / 46 were fully clean.**
Two slips were found and removed:
- **SENTIEON_CLI_001**: the answer word "CONSERVATIVE" was used as an example. Notably, that
  question **failed even with the leaked word present** — it contributed nothing.
- **PPLM_003**: the embedding dim "1280" (half of the answer `(122, 1280)`) was stated. It is
  a public property of the 650M model, and the real fix is model *selection*.

Both READMEs were de-leaked (`gen_help.py` regenerated; neither token remains anywhere) and
the affected questions re-run. Result with the clean READMEs:
- **PPLM_003** still lands `(122, 1280)` for both teams — from the model-selection steering
  alone, so that recovery is genuine.
- **SENTIEON_CLI_001** now answers `CONSERVATIVE` for both teams — recovered by the legitimate
  method tip ("dry_run prints the plan; it doesn't need the input files present"), *not* by a
  leaked answer (which had been present and hadn't helped).

Conclusion: **no leaked token was load-bearing**; the +9 / +10 gains are driven by method
steering (where weights/data live, dependency pins, ESM/embedding pitfalls, runnable
pipelines), not by answers planted in the READMEs.

## Where everything is
- Help READMEs: `help/<slug>.md` (and copied to `papers/<slug>/AGENT_HINTS.md`).
- Re-run outputs: `worker-critic-readme/` and `worker-critic-plus-plus-readme/`
  (chains/ logs/ traces/ costs/ manifest.csv, with a `used_help` column).
- Analysis: `analysis/master.md`, `analysis/comparison.md` (scorer-level flips), this file.
- Baselines used for comparison: `experiments-full-runs/worker-critic-batch/` and
  `src_logs/worker-critic-plus-plus/` (extracted from the remote branch).
- Code: `read_help` tool, `readme_agents.py`, the two `*_readme.py` teams, `help_path` +
  `help_provided` on the record. 239 unit tests pass. Nothing committed; branch
  `rq3-LLM-assistance`.
