# RQ3 README-assist — second pair (solo + HITL-autonomous) — PLAN & TRACKER

**Goal.** Mirror the help-README experiment for the two remaining agents — **solo** and
**human-in-the-loop (autonomous)** — exactly as done for worker-critic / worker-critic-plus-plus.
Author a NEW shared set of per-paper READMEs distilled from **these two agents' own**
autonomous failures, wire them to read it, run all 46 questions with it, save everything,
audit (incl. an answer-leak check), and summarize vs the autonomous baselines.

**Approach = #1 (mirror):** one shared README set authored from solo+HITL *combined* failures,
applied to both — same as the first pair. (Tips are about the tasks, so they're agent-agnostic.)

**Constraints.** Run autonomously — no questions to the user. Keep checking. Don't push unless
asked. Stay on branch `rq3-LLM-assistance`. Keep this file updated so progress survives resets.

## Data sources (local)
- solo baseline: `experiments-full-runs/solo-batch/` (chains+logs+AUDIT.md; 44 chains)
- HITL baseline: `experiments-full-runs/human-in-the-loop-batch/` (chains+logs+AUDIT.md; 39 chains)
- 46-question scope: `questions/<slug>.json` (copied from the first README experiment)
- Reuse where possible: the FIRST pair's READMEs (`../2026-06-07-rq3-readme-assist/help/`) as a
  starting reference, but re-derive from solo+HITL failures (their give-up/wrong patterns differ).

## Output layout (this dir)
- `help/<slug>.md` — the new shared READMEs (gen_help.py)
- `solo-readme/`, `human-in-the-loop-readme/` — the two run output dirs (chains/logs/costs/traces/manifest)
- `analysis/` (master, comparison), `SUMMARY.md`, `run_readme_sweep.py`, `gen_help.py`, `compare.py`

## Phases / checklist
- [x] P0 Setup: new eval dir, copy questions (18/18), locate solo+HITL baselines+AUDITs
- [ ] P1 Analyze solo + HITL failures per question (AUDITs + chains; mine winning chains for fixes)
- [x] P2 Authored 18 shared READMEs (gen_help.py = de-leaked first-pair base + solo/HITL additions:
      install-deps-yourself, SAM2 automatic-generator mode, SEGMA CPU, GWAS run-to-completion/path).
      Answer-leak scan clean (only hit = char '0' in "exit code 0", not GWAS_002's answer).
- [x] P3 **ARCHITECTURE done:** solo-readme = run_solo + create_react_agent_readme + _with_hints.
      human-in-the-loop-readme = delegate to run_human_in_the_loop with _with_hints-injected question
      (HITL crew UNCHANGED — help just prepended, propagates triage->setup->exec). Both registered
      (apply_setup=False), registry tests updated, 241 tests pass. _with_hints sets help_injected flag.
- [ ] P3-old **ARCHITECTURE CHECK + changes (do BEFORE running):**
    - `solo-readme`: write `run_solo_readme` — mirror `run_solo` but use `create_react_agent_readme`
      (already exists: base worker + read_help) and inject the help preamble. Expected: SIMPLE.
    - `human-in-the-loop-readme`: READ `human_in_the_loop.py` (281 lines, multi-stage triage→setup→
      execution+critic, uses ask_human). Decide where the README goes (the EXECUTION worker: add
      read_help to its tools + inject help into its input). Keep the integrity guard. Expected: INVOLVED.
    - Register both teams in `teams/__init__.py` (apply_setup=False for both, matching baselines).
    - Update registry tests (`test_teams.py`, `test_environment_agent.py`); run full suite (must pass).
- [ ] P4 Runner: copy/adapt `run_readme_sweep.py` into this dir (uses this dir's help/ + questions/),
    parameterized by team. solo + HITL run via `react_main --team <t>` headless (HITL ask_human degrades).
    Start at 600s cap; re-run timeouts at 1800s (help makes agents work harder). Fresh venv per question.
- [x] P4 Runner copied (TIMEOUT_S=1800 from the start, since HITL is slow + help makes agents work harder);
      compare.py adapted for solo+HITL baselines (canonical IDs, match by ID). Smoke: solo-readme SC_FRAMEWORK_001
      correct, help_provided=True, team=solo-readme, venv clean.
- [x] P5 DONE: solo 46/46; HITL 46/46 (SCISTREECNA_003 retried -> blocked = confirmed regression). venvs clean.
- [x] P6 DONE: compare.py + hand-audit + integrity (answer-leak scan CLEAN; recoveries grounded) + SUMMARY.md.
  FINAL VALIDATED: solo 17->28 effective (+11; ~13 recovered/2 regressed, $4.74);
  HITL 21-23->~32/45 (~+10; ~15 recovered incl. SAM2 via new tip/~3 regressed, ~$9).
  Cross-experiment: README helps ALL 4 agents (wc +9, plus-plus +10, solo +11, HITL ~+10).
  Note: SCISTREECNA_003 HITL retry still running; will be a recovery or a confirmed regression.

## Baselines (from AUDIT.md)
- solo: **17/46 effective-correct**, 4 truly wrong (ARCADIA_003 FP, CROSSPPI_004, CROSSPPI_006 ESM, SAM2_002 322 masks),
  6 legit-blocked, **17 GAVE UP (solvable)**, 2 timeout. Solo-specific: NO install-retry → gave up on GWAS_002 (numpy)
  and SAM2_001 (PIL); SEGMA claimed GPU (CPU works).
- HITL (autonomous): **21–23/46 effective-correct**, 12 truly wrong (incl. SAM2_001/002 wrong mode=3 masks, PPLM_001
  -10.66, CROSSPPI_003/004/006, GWAS_003 crash, LARIS_002 guessed), 4 legit-blocked, **7 timeouts** (multi-stage is slow).

## New solo/HITL-specific README tips to ADD (beyond the first pair's shared set)
- General: if an import fails, INSTALL the dep yourself (pip install …) and re-run — don't assume auto-install (solo has none).
- SAM2: use the AUTOMATIC mask generator over the whole image (not single-point/box prompting), default settings
  (HITL got 3 masks = single-prompt; solo got 322 = bad params).
- SEGMA: runs on CPU — don't give up claiming GPU required.
- GWAS: actually RUN the sim to completion; watch for a duplicated `workspace/workspace/` path bug; don't report a guess.
- (Carry over de-leaked first-pair tips: TabPFN cached v2/no token, PPLM weights+numpy<2+650M, CrossPPI ESM strip/install,
  RegFormer cell-emb pipeline, LARIS/distortions/scistreecna inputs, ARCADIA grid-count, CyteOnto labels.)

## Progress log
- 2026-06-07: P0+P1 done. Baselines recorded. Heavy overlap with first pair + solo/HITL-specific patterns above. Authoring READMEs (P2).
