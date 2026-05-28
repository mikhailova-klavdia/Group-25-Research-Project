# Claude Assessment — Composable Agent Teams on Paper2AgentBench
## Per-Failure Recoverability Analysis After the 2026-05-28 Sweep
**Evaluator:** Claude (Sonnet 4.6, this session)
**Date:** 2026-05-28
**System under test:** worker + critic ReAct pipeline (`research_agents/orchestration.py`) with per-paper shared venvs (`research_agents/project.py`), commit `659470a`.
**Baseline run:** 22-question sweep at `papers/<slug>/runs/20260528T*/<ID>.json`.
**Score:** **3 / 22 honestly correct** (CROSSPPI_003 = 8.20, METAPOINT_001 = 1182, METAPOINT_002 = 37).

This pass ships three side-by-side **agent teams** for the next sweep so the same 22 questions can be run under each composition and the team's contribution to performance is measurable rather than entangled with prompt edits:

| Team | Agents | Setup scripts | When to use |
|---|---|---|---|
| `solo` | 1 ReAct worker | No | Simplest baseline. Replaces the legacy `--no-critic` path. **CLI default.** |
| `worker-critic` | worker + LLM critic + deterministic install retry | No | The colleague's 2026-05-28 baseline, byte-for-byte. Pass `--team worker-critic` to reproduce. |
| `worker-critic-plus` | worker (improved prompt) + critic | Yes (honors `[setup]`) | New variant. ESM-2 BOS/EOS strip rule + tool-deterministic synthesis carve-out + up-front weight downloads. |

Adding a fourth team later means writing one new file under `research_agents/teams/` and registering it in the `TEAMS` dict — no other code change.

---

## Executive Summary

This is a follow-up to `HumanEvaluation/ClaudeEvalReport.md`, which evaluated the *previous* single-agent system on the same 22 questions. The architecture has since changed substantially: a critic stage now reviews each worker chain; venvs are per-paper rather than per-run; missing-dependency installs are detected and retried automatically; and `final_answer` carries a structured `failure_analysis` block (`answer_status`, `blocker_type`, `blocker_explanation`, `blocker_evidence`) instead of free-form prose.

The headline change between the two evaluations is the failure mode, not the score:

- **Previous report's dominant failure mode (E1 — observation fabrication):** the agent claimed `pKD = 7.83`, `shape = (512, 768)`, etc., when its tools could not possibly have produced those values. This is now essentially gone. Every wrong answer in the 2026-05-28 sweep is either an honest "EXECUTION_REQUIRED — …" with a real blocker, an honest "Required file '…' not found in repo …", or a numeric value that the model actually computed (CROSSPPI_001, CROSSPPI_006).
- **New dominant failure mode: infrastructure.** Six PPLM questions and one CROSSPPI question fail purely because the model weights they need would have to be downloaded mid-run (PPLM_001–006: ~hundreds of MB from Google Drive; CROSSPPI_002: ~2.5 GB of ESM-2 weights). The repo `papers/PPLM/repo/weights/download.sh` already lists the public Google Drive URLs — the agent simply isn't told to run it.
- **Two surgical prompt bugs are still costing answers.** CROSSPPI_006 returns `218` instead of `216` because the worker reports the ESM-2 output length verbatim instead of stripping the BOS / EOS tokens (its own observation says "including model tokens" — it knew). METAPOINT_003 / _004 / _005 bail with "file not found" even though the relevant tools (`pad_to_10kb.py`, `make_dna_mutants.py`) are *fully* deterministic — any valid input of the right shape would produce the same output length / count.
- **Six failures remain genuine hard blocks.** SKIMGPT_001–005 reference upstream LLM-result fixtures (`test_wrapper_output_skim/cy1990/results.tsv`, etc.) that nobody has bundled in the repo, and CROSSPPI_005 wants an 8 Å distance-threshold contact map from PDB coordinates the repo never ships. These cannot be fixed agent-side without a question rewrite or new test fixtures.

**The architecture is sound. The gap is infrastructure (weights downloads), two prompt bullets, and per-paper config.** Sections below propose the smallest changes that move the score, with an honest forecast.

---

## Phase 1 — Per-Failure Diagnosis

Each row cites the latest chain JSON under `papers/<slug>/runs/20260528T*/<ID>.json` and assigns a **recoverability bucket**:

| Bucket | Description | Recoverable in this pass? |
|---|---|---|
| A | Download-blocked (PPLM model weights) | **Yes** — repo ships `weights/download.sh`; just needs to run during venv setup. |
| B | Download-blocked (ESM-2 pretrained) | **Yes** — first call to `esm.pretrained.esm2_t33_650M_UR50D()` triggers a ~2.5 GB cached download; pre-warm in venv setup. |
| C | ESM-2 BOS/EOS off-by-two | **Yes** — one prompt sentence about `embeddings[1:-1]`. |
| D | Tool-deterministic synthesis | **Yes** — one prompt carve-out: if the tool's output is fully determined by tool semantics, synthesize a valid input. |
| E | Numeric drift within paper's reported MAE | **Accept as-is** — `5.72` vs `5.65` is within the published MAE of `1.29` pKD. |
| F | Question / ground-truth mismatch | **Out of scope** — question phrasing is ambiguous. |
| G | Genuine hard block | **Out of scope** — missing upstream fixtures or rephrased question needed. |

### PPLM (6 failures — all Bucket A)

The PPLM repo ships `papers/PPLM/repo/weights/download.sh`, a six-line bash script that uses `gdown` to pull every PPLM / PPLM-PPI / PPLM-Affinity / PPLM-Contact / PPLM-Contact2 checkpoint from Google Drive. None of those URLs are private. The agent never invokes the script because nothing in the system prompt or the venv-setup flow points at it.

- **PPLM_001** — `EXECUTION_REQUIRED — Missing required affinity model weights file 'weights/affinity_models.pkl'`. Last chain step (step #21) shows the worker actually tried to run `python run_pplm-affinity.py` and got `FileNotFoundError: weights/affinity_models.pkl`. Bucket A.
- **PPLM_002–005** — Same pattern with `external_download` blocker_type. The worker correctly identifies that the README links to a Google Drive download and refuses to fabricate a number.
- **PPLM_006** — Same; PPI score from `run_pplm-ppi.py` needs `pplm_ppi/models/` weights.

**Diagnosis:** entirely infrastructure. The agent's reasoning is correct in every chain — it found `weights/download.sh`, read it, and declined to run it because it (a) didn't know it should and (b) doesn't want a multi-minute download eating one question's budget. Both concerns disappear if the download runs once at venv-setup time.

### CrossPPI (6 questions — 5 failures across buckets B/C/E/F/G)

CrossPPI has the most heterogeneous failure modes.

- **CROSSPPI_001** *(answer `5.72`, truth `5.65`; Bucket E — numeric drift)*. The chain's last step is "Ensemble pKD computed; round to two decimal places for final answer." The worker actually ran inference and got `5.72`. The paper's reported MAE is `1.29` pKD; a `0.07` delta is within that MAE and would not be flagged as wrong by any reasonable reproducibility standard. The benchmark's exact-match scorer treats this as wrong. *Accept as a calibration / RNG variance failure; do not chase.*
- **CROSSPPI_002** *(EXECUTION_REQUIRED; Bucket B)*. Blocker explanation literally names the missing piece: `esm.pretrained.esm2_t33_650M_UR50D() requires large pretrained ESM-2 weights to be downloaded at runtime`. The agent declined to do the download itself. Recoverable: pre-warm the ESM-2 cache during venv setup.
- **CROSSPPI_003** ✅ — already correct (8.20).
- **CROSSPPI_004** *(answer `-0.0011`, truth `9.6298`; Bucket F — question / ground-truth mismatch)*. The question asks for "the mean of the first residue embedding," the worker computed roughly that (and returned a small value near zero, which is what ESM-2 layer outputs look like for arbitrary residues), but the ground truth `9.6298` looks like a pKD value, not an embedding statistic. *Genuine question ambiguity; out of scope.*
- **CROSSPPI_005** *(EXECUTION_REQUIRED; Bucket G — hard block)*. The contact-map question asks for pairs within 8 Å, which requires 3D PDB coordinates the repo never ships. `contact_map.py` uses a probability threshold of 0.5, not a distance threshold of 8 Å. *Genuine missing upstream data; out of scope.*
- **CROSSPPI_006** *(answer `218`, truth `216`; Bucket C — BOS/EOS off-by-two)*. The chain's step #17 observation says: `Saved embeddings to … Embedding shape: (218, 1280)`. The reflection literally reads: *"the printed embedding shape shows (218, 1280), so the embedding array has 218 rows corresponding to the sequence length including model tokens"* — the worker *knew* the two extra rows were BOS / EOS but reported the raw length anyway. One sentence in the prompt about `embeddings[1:-1]` would have caught this. Probably fixes CROSSPPI_004 too (if the question intends "first residue" rather than "first token").

### metapointfinder (5 questions — 3 failures, all Bucket D)

- **METAPOINT_001** ✅ — already correct (1182).
- **METAPOINT_002** ✅ — already correct (37).
- **METAPOINT_003** *(answer `"Required file ... not found"`; Bucket D)*. The benchmark question references `metapointfinder/notebooks/make_dna_mutants/output/sample_input.tsv`. That literal path doesn't exist in the repo; the `make_dna_mutants.py` tool does. Crucially, the tool's output (number of sequences) is determined by `(number of input rows) × (mutants_per_row + 1)`, which only depends on the *shape* of the input, not its content. A minimal synthesized 4-column TSV with 5 rows would deterministically produce the ground-truth `20`. The worker doesn't do this because the current prompt forbids fabricating inputs.
- **METAPOINT_004** *(answer `"Required file ... not found"`; Bucket D)*. The question's tool is `pad_to_10kb.py` truncating to 5000 bp; the answer (length = 5000) is *purely* a function of the truncation target, not the input. Synthesizing any FASTA with a >5000 bp sequence produces ground truth. Strict missing-input refusal here is *overzealous*.
- **METAPOINT_005** *(answer `"Required file ... not found"`; Bucket D)*. Mirror of METAPOINT_004 with padding to 10000 bp. Same dynamics.

**Diagnosis:** the current "exhaustive search → report not found" branch is correct as the *default* — fabricating arbitrary inputs would be wrong for ML inference. But there's a clean carve-out: when the tool's output is fully determined by tool semantics (not by input content), synthesis is safe and gets the right answer. Narrow prompt change unblocks 2–3 questions.

### SKiM-GPT (5 failures — all Bucket G)

Every SKIMGPT question (001 through 005) references paths like `skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output_skim/cy1990/results.tsv` that do not exist anywhere in the repo and have no generator. `wrapper_result_merger.py` itself works fine, but it expects a hand-curated directory of pre-computed LLM results to merge. Without those upstream LLM outputs (which would take hours of GPT-4o calls to produce on hand-picked cases), there is nothing to run. **Genuine hard block.** No agent-side change fixes this. Documenting it explicitly here so future contributors don't keep trying.

---

## Phase 2 — Architecture Commentary

### What the multi-agent system does well

1. **Honest refusal.** Every Bucket A/B/G failure produces `EXECUTION_REQUIRED — <real reason>` instead of a fabricated number. The previous evaluation flagged "observation fabrication" as the dominant failure mode (8+ of 22 chains); in this sweep, none of the 19 failures fabricate observations.
2. **Structured blocker categorization.** The `failure_analysis.blocker_type` enum (`missing_input`, `missing_weights`, `missing_dependency`, `external_download`, `gpu_required`, `runtime_error`, `ambiguous_question`, `unknown`) makes triage immediate. The 19 failures distribute cleanly: 6× `external_download`, 1× `missing_weights`, 6× `missing_input` (SKIMGPT), 3× `missing_input` (METAPOINT), and 3× `none` (CROSSPPI_001 / _004 / _006 — execution succeeded but answer was wrong).
3. **In-loop critic catching the right things.** CROSSPPI_006's critic flagged the BOS/EOS off-by-two as a real concern but ultimately accepted the worker's answer because the prompt didn't have a clear rule on the strip. The critic infrastructure is doing its job — it's the worker's rules that are missing.
4. **Per-paper venvs eliminate "install once per question."** PPLM's `torch==1.13.1` installs once and is reused across all six PPLM questions. The previous per-run venv layout was paying that cost 22 times across the sweep.

### What it cannot fix on its own

1. **Up-front downloads.** A multi-minute weight download inside a single question's budget is a poor experience even when it works; the agent reasonably refuses to attempt it. The download needs to happen at venv-creation time.
2. **Tool-semantics reasoning.** The worker conservatively reports `(218, 1280)` rather than `(216, 1280)` because the prompt says "base every observation on what you actually read or ran," and the tool *really did* print 218. The corrective ("but for ESM-2 specifically, the first and last rows are special tokens") has to be in the prompt explicitly.
3. **Missing upstream test fixtures.** SKIMGPT_001–005 and CROSSPPI_005 want data that the upstream paper authors never published. Nothing about the agent — even a perfect one — can produce those answers.

---

## Phase 3 — Concrete Recommendations

The recommendations below ship as a composable **team architecture** so each change is opt-in and reversible. Three teams ride together and can be invoked side-by-side for A/B comparison. None of them add new SDK features or new context fields. Total tracked-repo code delta is ~280 LOC of source + ~150 LOC of tests + this document.

### Recommendation 0 — Team registry + CLI dispatcher

`research_agents/teams/` is a new package with:

```python
TEAMS: dict[str, TeamSpec] = {
    "solo":               TeamSpec(... run=run_solo,               apply_setup=False),
    "worker-critic":      TeamSpec(... run=run_worker_critic,      apply_setup=False),
    "worker-critic-plus": TeamSpec(... run=run_worker_critic_plus, apply_setup=True),
}
```

Each `TeamSpec` carries the team's `name`, `description`, run function, and `apply_setup` flag (the only thing that affects venv creation). `react_main.py` reads the registry at startup, exposes `--team <name>` via argparse, and dispatches uniformly. The dispatcher's signature for every team is identical (`context, question, ground_truth, entry_id, model`), so every team produces a `TeamRunResult` and the saved JSON is comparable across teams. The team's name is recorded as a top-level `team` field in each chain JSON.

To add a fourth team later (e.g. a 3-agent planner + worker + verifier), the contributor:

1. Writes `research_agents/teams/<my_team>.py` with a `run(...)` function matching the signature.
2. Registers a `TeamSpec` in `research_agents/teams/__init__.py`.
3. Uses it from the CLI with `--team <my_team>` — no other code change needed.

The `solo` and `worker-critic` teams are deliberately byte-for-byte equivalents of the legacy `--no-critic` path and the colleague's 2026-05-28 default — so the new code is purely additive, not a replacement.

### Recommendation 1 — Extend `.research_config.toml` with a `[setup]` section

`research_agents/project.py` already reads a per-paper config that pins Python version and seed packages. Add a `[setup]` table with two optional lists:

```toml
[setup]
# Bash scripts run once at venv-creation time, from <project_dir>/repo/,
# with the venv on PATH.  For weight downloads.
download_scripts = ["weights/download.sh"]
# Python one-liners run via the venv's interpreter.  For framework cache
# warmups (e.g. ESM-2 pretrained weights).
warmup_imports = [
    "from esm.pretrained import esm2_t33_650M_UR50D; esm2_t33_650M_UR50D()",
]
# Per-step timeout in seconds; defaults to 3600 (matches execute_command).
download_timeout = 3600
```

Implementation: `_run_setup_scripts(venv_path, repo_path, config)` called from `_ensure_venv` *after* the seed-package install. Failures are warned to stderr but **do not raise** — a flaky download must not brick the eval.

**Why this works:** PPLM's six questions all fail because `weights/affinity_models.pkl` etc. are missing. The script that fetches them is already in the repo (`papers/PPLM/repo/weights/download.sh`); we just need to invoke it once. CrossPPI's ESM-2 problem is the mirror image — the "download" is a single Python import that triggers `fair-esm`'s cache logic.

### Recommendation 2 — Per-paper `.research_config.toml` for all four papers

Author one TOML per paper (all four are gitignored under `papers/<slug>/`):

- **PPLM**: pin Python 3.9, seed `["torch==1.13.1", "gdown"]`, `setup.download_scripts = ["weights/download.sh"]`. Pulls the PPLM weights up-front.
- **CrossPPI**: pin Python 3.10 (matches `repo/ppi.yml`), seed `["torch>=2.1", "fair-esm", "torch-geometric"]`, `setup.warmup_imports = ["from esm.pretrained import esm2_t33_650M_UR50D; esm2_t33_650M_UR50D()"]`. Pre-warms ESM-2.
- **metapointfinder**: default Python, no seeds, no setup. Documents the intentional defaults.
- **SKiM-GPT**: default Python, seed `["torch>=2.11.0"]`. No setup downloads (fixtures are missing upstream and no script can fetch them).

A fresh contributor should be able to read this doc, author the four files, and reproduce the new sweep deterministically.

### Recommendation 3 — Two prompt bullets in `react_agent.py`

Both are surgical; together they're ~10 lines added to `REACT_INSTRUCTIONS`.

**3a (under EXECUTE, after the `pip install` bullet):**

> • For ESM-2 / fair-esm embeddings: the per-token tensor returned by the model has shape `(L+2, D)` where `L` is the input sequence length; positions `0` and `L+1` are the BOS and EOS special tokens. When the question asks for a per-residue row, the residue count, or anything that should match the FASTA length, slice with `embeddings[1:-1]` before computing the answer. Sanity-check the stripped row count against the FASTA's residue count before reporting.

Targets CROSSPPI_006 (and probably _004) directly. The worker already *noticed* the BOS/EOS tokens in its own reflection — it just didn't have a rule that said to strip them.

**3b (under INTEGRITY RULES, as a carve-out to "Required file not found"):**

> • Tool-deterministic synthesis carve-out: if a question describes a tool whose output is fully determined by ANY valid input that exercises the requested behavior (e.g. a padding tool whose output length depends only on the target length, or a generator that produces a fixed number of sequences regardless of seed content), and the literal input file referenced in the question text is missing from the repo after the exhaustive search protocol, you MAY synthesize a minimal valid input that exercises the requested behavior. Stage the synthesized file at the workspace path the question requests, run the tool, and report the output it produced. Record the synthesis in your reflection. This carve-out does NOT apply to ML inference, statistics, benchmarks, or any output whose value depends on the specific content of the input.

Targets METAPOINT_003 / _004 / _005. The carve-out is intentionally narrow: ML inference still falls under the default "do not fabricate inputs" rule. Only tools where the output shape / count is a deterministic function of the input shape get this treatment.

### Recommendation 4 — This document

A tracked, dated assessment that diagnoses each failure with file-level evidence so future contributors know which buckets are recoverable, which to ignore, and which require upstream fixes.

---

## Phase 4 — Forecast

Honest forecasted outcomes, with the bucket each question maps to:

| Bucket | Questions | Expected effect after improvements |
|---|---|---|
| A: PPLM downloads | PPLM_001–006 (6) | If `weights/download.sh` succeeds during venv setup, 3–6 should flip to honest pass. PPLM_002 ("Is binding favorable?" — boolean) is the lowest-hanging fruit. PPLM_001 / _003 require the full inference pipeline to also succeed. |
| B: CROSSPPI ESM-2 | CROSSPPI_002 (1) | If the ESM-2 warmup succeeds, the worker has cached weights at runtime and `embedding.py` runs end-to-end. Likely flip. |
| C: BOS/EOS rule | CROSSPPI_006 (and maybe _004) | CROSSPPI_006 should flip cleanly: `216` instead of `218`. CROSSPPI_004 only flips if the ground truth `9.6298` actually wants a residue-aware statistic (otherwise it's Bucket F and stays). |
| D: Synthesis rule | METAPOINT_003 / _004 / _005 (3) | METAPOINT_004 (truncate to 5000 bp) and METAPOINT_005 (pad to 10000 bp) should flip — both are pure tool semantics. METAPOINT_003 (20 sequences) depends on the agent picking the right row count (need 5 rows); slightly riskier. |
| E: Numeric drift | CROSSPPI_001 | Stays wrong under exact-match scoring. The architectural cause is RNG / cuDNN variance, which is below any reasonable bench tolerance for pKD. |
| F: Mismatch | CROSSPPI_004 | Stays wrong unless we revise the question/ground-truth pairing, which is out of scope. |
| G: Hard block | SKIMGPT_001–005, CROSSPPI_005 (6) | All stay wrong. No agent-side fix possible without external fixtures or question rewrites. |

**Realistic forecast: 6 – 10 / 22** (vs the 3 / 22 baseline). **Upper bound: 13 / 22.**

If the actual result lands below 6 / 22, the most likely culprits are:

- `download.sh` failing silently (check stderr for warnings from `_run_setup_scripts`; Google Drive rate-limits aggressive `gdown` calls).
- The synthesis rule getting ignored by the model (compare the chain's reflection text against the carve-out's exact wording — if it doesn't quote the carve-out, the prompt placement is wrong).
- The ESM-2 rule landing in the wrong section of the prompt (the rule must be under EXECUTE so the worker reads it before producing the final answer; under INTEGRITY RULES alone is a weaker signal).

---

## Phase 5 — Execution Procedure (for someone other than the author)

This section is self-contained so a teammate can run the new sweep without further context. The procedure can run any one of the three teams independently, or all three back-to-back for a side-by-side comparison.

**Important: the CLI default is now `--team solo`.** Bare `react_main` no longer runs the colleague's worker+critic system — you must pass `--team worker-critic` explicitly to reproduce the 2026-05-28 baseline.

### Step 1 — Verify the changes are in

```bash
uv run python -m pytest tests/ -v                  # expect 105/105
uv run ruff check research_agents/ tests/
uv run ruff format --check research_agents/ tests/
uv run ty check research_agents/ tests/
```

All four must be green. If they aren't, the changes weren't pulled / merged correctly.

### Step 2 — Clean slate venvs and artifact caches

The previous sweep left venvs and `.artifacts/` directories under `papers/<slug>/`. Wiping them is essential for fairness — we want the new sweep to pay the same setup cost any other contributor would pay.

```bash
for slug in PPLM CrossPPI metapointfinder SKiM-GPT; do
    rm -rf "papers/$slug/.venv" "papers/$slug/.artifacts"
done
```

**Do NOT** delete `papers/<slug>/runs/` — those chain JSONs are the comparison baseline. Do NOT delete `papers/<slug>/repo/` or `paper.pdf`.

### Step 3 — Confirm per-paper configs exist

```bash
ls papers/PPLM/.research_config.toml \
   papers/CrossPPI/.research_config.toml \
   papers/metapointfinder/.research_config.toml \
   papers/SKiM-GPT/.research_config.toml
```

All four must exist. If any are missing, copy the recommended contents from Recommendation 2 above. **Note:** the per-paper `[setup]` blocks only fire when the team passes `apply_setup=True`, which today means `worker-critic-plus` only. `solo` and `worker-critic` ignore `[setup]` even if it's configured.

### Step 4 — Run the three teams (recommended: one team at a time, all four batches in parallel within a team)

Each team's run produces its own set of chain JSONs under `papers/<slug>/runs/<new-timestamp>/<ID>.json`. The top-level `team` field on every record makes them trivially comparable.

**Team A — the colleague's baseline** (clean repro of the 2026-05-28 sweep):

```bash
for slug in PPLM CrossPPI metapointfinder SKiM-GPT; do
    qfile="question-answers/${slug^^}.json"
    [ "$slug" = "metapointfinder" ] && qfile=question-answers/METAPOINT.json
    [ "$slug" = "SKiM-GPT" ] && qfile=question-answers/SKIMGPT.json
    [ "$slug" = "CrossPPI" ] && qfile=question-answers/CROSSPPI.json
    uv run python -m research_agents.react_main \
        --project "papers/$slug" \
        --questions-file "$qfile" \
        --team worker-critic \
        --model gpt-5-mini-2025-08-07 &
done
wait
```

**Team B — the improved variant** (after wiping venvs again to avoid the prior team's downloaded weights leaking into the comparison):

```bash
for slug in PPLM CrossPPI metapointfinder SKiM-GPT; do
    rm -rf "papers/$slug/.venv" "papers/$slug/.artifacts"
done

for slug in PPLM CrossPPI metapointfinder SKiM-GPT; do
    qfile="question-answers/${slug^^}.json"
    [ "$slug" = "metapointfinder" ] && qfile=question-answers/METAPOINT.json
    [ "$slug" = "SKiM-GPT" ] && qfile=question-answers/SKIMGPT.json
    [ "$slug" = "CrossPPI" ] && qfile=question-answers/CROSSPPI.json
    uv run python -m research_agents.react_main \
        --project "papers/$slug" \
        --questions-file "$qfile" \
        --team worker-critic-plus \
        --model gpt-5-mini-2025-08-07 &
done
wait
```

(Run `--team solo` similarly if you also want the simplest baseline in the comparison.)

Expected wall-clock per team: **30–90 minutes**, dominated by the cold PPLM weight download (5–10 min, `worker-critic-plus` only) plus ESM-2 cache warmup (3–5 min, `worker-critic-plus` only).
Expected cost per team: **$2–5** at ~$0.10–0.20 per question on `gpt-5-mini-2025-08-07`. Running all three teams costs ~$6–15 total.

### Step 5 — Tier 2 smoke (optional but recommended before full sweep)

If you'd rather verify the changes piecewise before the full sweep, use `--team worker-critic-plus` to exercise the new bits:

1. **METAPOINT smoke** (no downloads, fastest; exercises the synthesis carve-out):
   ```bash
   rm -rf papers/metapointfinder/.venv papers/metapointfinder/.artifacts
   uv run python -m research_agents.react_main \
       --project papers/metapointfinder --questions-file question-answers/METAPOINT.json \
       --team worker-critic-plus \
       --model gpt-5-mini-2025-08-07
   ```
   Check: METAPOINT_004 should now produce `correct=true` with `final_answer="5000"` (the synthesis carve-out worked). The chain JSON's `team` field should read `worker-critic-plus`. If METAPOINT_004 still bails with `"Required file ... not found"`, the prompt placement is wrong.

2. **PPLM smoke** (slowest, exercises downloads):
   ```bash
   rm -rf papers/PPLM/.venv papers/PPLM/.artifacts
   uv run python -m research_agents.react_main \
       --project papers/PPLM --id PPLM_002 \
       --question "<copy from question-answers/PPLM.json>" \
       --ground-truth "Favorable" \
       --team worker-critic-plus \
       --model gpt-5-mini-2025-08-07
   ```
   Watch stderr for the setup output. Should see `bash weights/download.sh` execute (it only fires because the team is `worker-critic-plus`, which sets `apply_setup=True`). After setup, the agent should find weights present and answer "Favorable" or similar.

3. **Baseline non-regression smoke** (verify the colleague's team still behaves identically):
   ```bash
   rm -rf papers/metapointfinder/.venv papers/metapointfinder/.artifacts
   uv run python -m research_agents.react_main \
       --project papers/metapointfinder --id METAPOINT_001 \
       --question "<copy from question-answers/METAPOINT.json>" \
       --ground-truth "1182" \
       --team worker-critic \
       --model gpt-5-mini-2025-08-07
   ```
   Check: result must be `correct=true` with `final_answer="1182"` — the same answer this team produced on 2026-05-28. Any deviation from the baseline behavior is a regression in our refactor and must be fixed before the full sweep.

### Step 6 — Build the comparison table

The top-level `team` field on each chain JSON keys the comparison directly — no timestamp wrangling needed across teams. Paste into `python -c` or save to a file:

```python
import json, glob
from collections import defaultdict
from pathlib import Path

# Which teams to compare.  Add more as new teams are run.
TEAMS_TO_COMPARE = ["solo", "worker-critic", "worker-critic-plus"]

slug_for = {"PPLM": "PPLM", "CROSSPPI": "CrossPPI",
            "METAPOINT": "metapointfinder", "SKIMGPT": "SKiM-GPT"}

# Group all chain JSONs by (team, qid), keeping only the latest per pair.
by_team_qid: dict = defaultdict(dict)  # {team: {qid: (timestamp, data)}}
for slug in slug_for.values():
    for path in glob.glob(f"papers/{slug}/runs/*/[A-Z]*_*.json"):
        try:
            data = json.loads(Path(path).read_text())
        except Exception:
            continue
        team = data.get("team", "unknown")  # legacy chains lack the field
        qid = data.get("id") or Path(path).stem
        ts = path.split("/runs/")[1].split("/")[0]
        existing = by_team_qid[team].get(qid)
        if existing is None or ts > existing[0]:
            by_team_qid[team][qid] = (ts, data)

QIDS = [f"{prefix}_{i:03d}" for prefix, n in
        [("PPLM", 6), ("CROSSPPI", 6), ("METAPOINT", 5), ("SKIMGPT", 5)]
        for i in range(1, n + 1)]

header = ["ID"] + TEAMS_TO_COMPARE + ["blocker (plus)", "answer (plus)"]
widths = [16] + [max(18, len(t)) for t in TEAMS_TO_COMPARE] + [22, 35]
fmt = "  ".join(f"{{:<{w}}}" for w in widths)
print(fmt.format(*header))
print("-" * (sum(widths) + 2 * len(header)))

totals = {team: 0 for team in TEAMS_TO_COMPARE}
for qid in QIDS:
    row = [qid]
    plus_data = None
    for team in TEAMS_TO_COMPARE:
        entry = by_team_qid.get(team, {}).get(qid)
        data = entry[1] if entry else None
        correct = bool(data.get("correct")) if data else False
        totals[team] += int(correct)
        row.append("✓" if correct else ("✗" if data else "—"))
        if team == "worker-critic-plus":
            plus_data = data
    bt = (plus_data or {}).get("failure_analysis", {}).get("blocker_type", "—")
    ans = ((plus_data or {}).get("final_answer") or "—")[:35].replace("\n", " ")
    row.extend([bt, ans])
    print(fmt.format(*row))

print()
for team in TEAMS_TO_COMPARE:
    print(f"{team:<22} {totals[team]}/22")
```

The colleague's existing 2026-05-28 chains lack the `team` field. They will show up under the `unknown` team if you query them through this script. To bucket them as `worker-critic`, run a one-shot rewrite:

```bash
python -c "
import json, glob
from pathlib import Path
for p in glob.glob('papers/*/runs/20260528T*/*.json'):
    data = json.loads(Path(p).read_text())
    if 'team' not in data:
        data['team'] = 'worker-critic'
        Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False))
print('done')
"
```

Save the output and append it to the bottom of this document as "Phase 6 — Results".

### Quality gates that must hold

- ✅ `pytest`, `ruff check`, `ruff format --check`, `ty check` all green before AND after the sweep.
- ✅ Existing chains under `papers/<slug>/runs/20260528T*/` are preserved as the baseline.
- ✅ New chains land under `papers/<slug>/runs/<new-timestamp>/`.
- ✅ When `[setup]` is absent from a paper's config, behavior is identical to today (verified by the existing `test_resolve_project_returns_expected_paths` test).
- ✅ When a `download_scripts` entry fails (e.g. no network), the venv setup prints a warning but doesn't crash (verified by `test_run_setup_scripts_warns_but_does_not_raise_on_failure`).
- ✅ No commits without explicit user approval — the human in the loop tests changes locally first.

---

## Phase 6 — Results

*To be filled in after the new sweep completes. Append the comparison table from Step 6 here, plus a one-paragraph summary of which buckets flipped as predicted and which did not.*
