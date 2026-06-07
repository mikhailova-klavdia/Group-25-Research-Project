# RQ3 (pivot): Static help-README assistance — PLAN & TRACKER

**Goal.** For the 2 best autonomous teams (`worker-critic`, `worker-critic-plus-plus`),
analyze their ORIGINAL autonomous run logs, author a per-paper steering **README of tips**
(NOT the answer, NOT step-by-step — hints to steer, with most attention on the questions
they got WRONG), wire the agents to READ that README, then re-run all 46 questions WITH the
README and save every result. Deliverable: 2 full re-runs + a final summary.

**Constraints.** Do not push. Stay on branch `rq3-LLM-assistance`. Work autonomously
(no questions to user). Keep this file updated so progress survives context resets.

## Data sources (already staged locally)
- worker-critic (autonomous): `experiments-full-runs/worker-critic-batch/` (chains+logs+AUDIT.md+manifest)
- worker-critic-plus-plus (autonomous): `eval_runs/2026-06-07-rq3-readme-assist/src_logs/worker-critic-plus-plus/`
  (chains+AUDIT.md+manifest; extracted from `origin/experiments-full-runs-worker-critic-plus-plus`)
- 46-question scope: `eval_runs/2026-06-07-rq3-readme-assist/questions/<slug>.json` (id/question/ground_truth/repo_link)

## Output layout
- `analysis/` — per-question findings (status / where stuck / why wrong) for both teams
- `help/<slug>.md` — the 18 authored per-paper steering READMEs
- `worker-critic-readme/` and `worker-critic-plus-plus-readme/` — the 2 re-run output dirs
- `run_readme_sweep.py` — the runner (places help file alongside paper, runs, saves)

## Phases / checklist
- [x] P0 Setup: dirs, PLAN.md, extract plus-plus data, copy questions
- [x] P1 Analyze worker-critic per question (status/stuck/why) using AUDIT.md + chains + logs
- [x] P1 Analyze worker-critic-plus-plus per question (AUDIT.md + chains) -> analysis/master.md
- [x] P1b Mined winning chains for fixes; checked current data presence (PPLM/SAM2/tabpfn weights present; some inputs absent); read full tricky questions (ARCADIA_003=grid product, CROSSPPI_004/006 ESM, PPLM numpy<2/650M)
- [x] P2 Author per-paper help READMEs (18) -> help/<slug>.md (gen_help.py; tips only, answer-free)
- [x] P3 Architecture: ResearchContext.help_path; read_help tool (tools/help_tools.py);
        resolve_project sets help_path=project_dir/AGENT_HINTS.md; new factories
        (research_agents/agents/readme_agents.py); new teams worker-critic-readme +
        worker-critic-plus-plus-readme (apply_setup F/T to match baselines); tests added;
        239 tests pass. NOTE: static help (NO human in loop) -> fully autonomous re-runs.
- [x] P4 Runner: run_readme_sweep.py <team> — places help/<slug>.md -> papers/<slug>/AGENT_HINTS.md,
        runs each question (600s cap + max-turns 50, same as baselines), saves
        chains/logs/costs/traces/manifest(+used_help col), fresh venv per q, resumable. (smoke-testing)
- [~] P5 Run worker-critic-readme x46 -> save  (eval dir: worker-critic-readme/)
- [~] P5 Run worker-critic-plus-plus-readme x46 -> save  (eval dir: worker-critic-plus-plus-readme/)
  PASS 1 (600s cap) done: wc 39/46, pp 33/46 — the other 20 TIMED OUT (help directs more work
  than the give-up baselines, so 600s too tight). Bumped cap to 1800s, cleaned chainless manifest
  rows, RE-RUNNING just the missing 20 (resumable) [b11kh6ql4].
  EARLY RECOVERIES (help worked): wc recovered 6 (CROSSPPI_003/006, CYTEONTO_001, DISTORTIONS_005,
  METAPOINT_004/005); pp recovered 4 (CROSSPPI_003/006, REGFORMER_003, SAM2_002).
  REGRESSIONS to audit in P6: wc FADVI_003, SENTIEON_CLI_001; pp DISTORTIONS_001(36->8),
  METAPOINT_002(37->19), LARIS_003(blocked: h5ad genuinely absent).
- [x] P5 DONE: both teams 46/46 (re-run timeouts at 1800s). venvs clean.
- [x] P6 DONE: compare.py + hand-audit + SUMMARY.md.
  AUDITED RESULT: worker-critic 24->32 effective; worker-critic-plus-plus 26->36. help_provided 46/46 both.
- [x] P7 INTEGRITY AUDIT (did answers leak into READMEs?): grepped every GT vs help files.
  44/46 clean. 2 slips: SENTIEON ("CONSERVATIVE" as example; that Q had FAILED anyway) +
  PPLM_003 ("1280" dim, public model property). De-leaked gen_help.py, re-ran the 2 Qs x2 teams:
  PPLM_003 still (122,1280) via model-selection steering; SENTIEON now CORRECT via legit dry_run
  tip (it failed even WITH the leak). No leaked token was load-bearing.
  FINAL VALIDATED: worker-critic 24->33 (+9; 10 recovered/1 regressed, $6.70);
  worker-critic-plus-plus 26->36 (+10; 13 recovered/3 regressed, $3.55). See SUMMARY.md.
- [ ] P6 Summary: assisted-README vs autonomous baseline (correct/wrong/blocked), per team

## Baseline correctness (from AUDIT.md)
- worker-critic: effectively right 24/46; truly wrong 3 (ARCADIA_003 scorerFP=162/6, CROSSPPI_004, CROSSPPI_006 ESM+2);
  7 legit-blocked; **11 GAVE UP but SOLVABLE** (CYTEONTO_001, LARIS_001/2/3, SCISTREECNA_003, DISTORTIONS_001/5/6,
  REGFORMER_003, SAM2_002 [ckpt present], TABPFN_001 [v2 weights cached]); 1 timeout (METAPOINT_005).
- worker-critic-plus-plus: correct 26/46; truly wrong 7 (ARCADIA_002 FP=162/6, CROSSPPI_003, CROSSPPI_004 ESM+2,
  DISTORTIONS_002 off-by-1, PPLM_001 wrong path, PPLM_003 dim 320 vs 1280, SCISTREECNA_001); 12 legit-blocked;
  1 integrity-block (PPLM_006). NOTE: plus-plus apply_setup=True (downloads weights), worker-critic apply_setup=False.
- NOTE: the two teams used slightly different per-paper ID numbering (e.g. ARCADIA_002/003 vs 001/002; METAPOINT vs METAPOINTFINDER).

## Key fixable themes for the READMEs
- Pre-downloaded weights the agent failed to find: TABPFN (cached v2, no token, clone caveat), SAM2 (ckpt present), PPLM (pplm_t33_650M.pt).
- Missing inputs that ARE obtainable (HITL ran them): LARIS adata_tonsil.h5ad, DISTORTIONS, REGFORMER embeddings.npy, SCISTREECNA, CYTEONTO labels.
- Conceptual bugs: ESM-2 strip BOS/EOS (embeddings[1:-1]) → CROSSPPI; use 650M model (1280-dim not 320) → PPLM_003; off-by-1 grouping → DISTORTIONS_002; ARCADIA question asks for 6 not 162/300.
- Dependency installs that failed: CrossPPI torch/esm, SAM2 torch/hydra.

## Progress log
- 2026-06-07: P0 done. Read both AUDITs. Baselines recorded. Building consolidated master table (P1).
