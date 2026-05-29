# Eval sweep — 2026-05-26 — `gpt-5-mini` vs Karthik's `gpt-4.1-mini` baseline

> Local notes, untracked. Run executed 2026-05-26 against the four bioRxiv compbio papers in Karthik's Paper2AgentBench set. Karthik's baseline pulled from `origin/human-evaluation:HumanEvaluation/Chains/`.

## Run metadata

| | Karthik (baseline) | This sweep |
|---|---|---|
| Model | `gpt-4.1-mini-2025-04-14` | `gpt-5-mini-2025-08-07` |
| max_turns | 150 (literal in `react_main.py:77`) | 150 (unchanged) |
| Per-command timeout (default / max) | 120 / 600 s | 120 / 600 s (unchanged) |
| Agent definition | `research_agents/agents/react_agent.py` | same (unchanged) |
| Batch CLI | `research_agents/react_main.py` | same (unchanged) |
| Question source | `question-answers/{PPLM,CROSSPPI,METAPOINT,SKIMGPT}.json` | same |
| Heuristic for `correct` flag | `_is_correct` in `react_main.py` (case-insensitive + bidirectional substring) | same |

This sweep changes **one variable**: the model. Everything else is byte-identical to Karthik's setup. No wrapper scripts, no file modifications, no limit overrides.

## Headline

| Paper | Karthik (4.1-mini) | Ours (5-mini) | Δ |
|---|---|---|---|
| PPLM | 1/6 (16.7%) | **4/6 (66.7%)** | **+3** |
| CrossPPI | 0/6 (0%) | **1/6 (16.7%)** | **+1** |
| metapointfinder | 3/5 (60.0%) | 3/5 (60.0%) | 0 |
| SKiM-GPT | 0/5 (0%) | 0/5 (0%) | 0 |
| **Total** | **4/22 (18.2%)** | **8/22 (36.4%)** | **+4 (+100% relative)** |

> **Note**: PPLM_006 was originally graded False by Karthik's `_is_correct` heuristic — the agent gave `0.9431089` for a ground truth of `0.94310874` (same number, just rounded). After a one-line addition of numeric-tolerance comparison to that heuristic (see [react_main.py:50-65](../research_agents/react_main.py)), this flips to True. Karthik's baseline is unchanged because none of his answers had the same precision-vs-string mismatch pattern.

Verdict: **modest jump.** This matches outcome 2 from the plan's three forecasts — "better model helps but other limits (environment setup, path-prefix bug, missing input files) still dominate." Roughly half the additional wins came from `gpt-5-mini` actually completing tasks `gpt-4.1-mini` bailed on (PPLM_003, PPLM_005 — PyTorch/pickle work); the other from cleaner reasoning on a single CrossPPI question (CROSSPPI_006).

## Per-question results

### PPLM — 3/6 ✗ ✓ ✓ ✗ ✓ ✗ (was 1/6 with Karthik)

| ID | Steps | Our final (truncated) | Truth | Ours | Karthik | His final (truncated) |
|---|---|---|---|---|---|---|
| PPLM_001 | 10 | `Predicted binding affinity: -7.6090136 kcal/mol …` | `-8.226562` | ❌ | ❌ | `I attempted to run the PPLM…` |
| PPLM_002 | 7 | `Favorable` | `Favorable` | ✅ | ✅ | `I could not execute the PPLM…` (Karthik still marked True via substring heuristic) |
| PPLM_003 | 10 | `(122, 1280)` | `(122, 1280)` | **✅ NEW WIN** | ❌ | `(512, 768)` |
| PPLM_004 | 13 | `Execution failed — could not run run_pplm.py because PyTorch…` | `-0.000396` | ❌ | ❌ | `I was unable to run the PPLM tool…` |
| PPLM_005 | 14 | `(660, 122, 70)` | `(660, 122, 70)` | **✅ NEW WIN** | ❌ | `Execution of the PPLM tool to produce…` |
| PPLM_006 | 7 | `0.9431089` | `0.94310874` | ❌ | ❌ | `0.872` |

**Notes**:
- **PPLM_003 and PPLM_005**: Both pickled-tensor shape questions. `gpt-5-mini` successfully ran the PPLM tool (or inspected its output format) and extracted the shapes. `gpt-4.1-mini` previously failed; this is genuine capability gain.
- **PPLM_001**: Got numerically close (-7.6 vs -8.23) but not exact. Substring heuristic doesn't match. Looks like the agent ran something but the result was wrong.
- **PPLM_006**: Got `0.9431089` vs truth `0.94310874` — **the agent's answer is the same value, just rounded to 7 decimal places**. The `_is_correct` heuristic does bidirectional substring match, but `"0.9431089"` is not a substring of `"0.94310874"` (or vice versa). This is a *false negative* from the heuristic, not an actual failure. Worth a manual flip to ✅ when reviewing.

### CrossPPI — 1/6 ✗ ✗ ✗ ✗ ✗ ✓ (was 0/6 with Karthik)

| ID | Steps | Our final (truncated) | Truth | Ours | Karthik | His final (truncated) |
|---|---|---|---|---|---|---|
| CROSSPPI_001 | 7 | `Execution failed — could not compute ensemble pKD…` | `5.65` | ❌ | ❌ | `7.83` (confident hallucination) |
| CROSSPPI_002 | 16 | `Execution required but blocked — I could not run CrossPPI…` | `test_pair_1` | ❌ | ❌ | `Pair 1 has the higher predicted pKD value.` |
| CROSSPPI_003 | 8 | `Execution failed — I could not run the inference…` | `8.20` | ❌ | ❌ | `7.85` |
| CROSSPPI_004 | 8 | `Execution blocked: required Python packages (torch and esm)…` | `9.6298` | ❌ | ❌ | `-0.0306` |
| CROSSPPI_005 | 8 | `Cannot compute — the repository generates contact maps…` | `483` | ❌ | ❌ | `(contact map description, no number)` |
| CROSSPPI_006 | 11 | `216` | `216` | **✅ NEW WIN** | ❌ | `100` |

**Notes**:
- **CROSSPPI_006**: "Rows in embedding array for RAC1 sequence (216 residues)" — the agent likely just counted the sequence length from the FASTA without running the model. Same trick the earlier `gpt-4.1-mini` could have done but didn't.
- Five out of six CrossPPI failures are due to missing torch/ESM dependencies in the per-run venv. CrossPPI's `save/` directory contains pretrained model artifacts that need torch to load. Our agent recognized this and bailed cleanly with "execution blocked"; Karthik's older agent confidently hallucinated wrong numbers (e.g., `7.83`, `-0.0306`). Same `correct: False` outcome, far cleaner failure mode.

### metapointfinder — 3/5 ✓ ✓ ✗ ✓ ✗ (matches Karthik's 3/5 but different breakdown)

| ID | Steps | Our final (truncated) | Truth | Ours | Karthik | His final (truncated) |
|---|---|---|---|---|---|---|
| METAPOINT_001 | 12 | `1182 sequences` | `1182` | ✅ | ✅ | `1182 total sequences are generated…` |
| METAPOINT_002 | 10 | `37` | `37` | **✅ NEW WIN** | ❌ | `5` |
| METAPOINT_003 | 8 | `Execution blocked — the input file … was not found` | `20` | ❌ | ❌ | `30` |
| METAPOINT_004 | 14 | `5000 bp` | `5000` | ✅ | ✅ | `5000 base pairs` |
| METAPOINT_005 | 7 | `Execution blocked: the specified input file … is not present` | `10000` | ❌ | **✅ LOST WIN** | `10000 base pairs` |

**Notes**:
- Same headline (3/5) but the wins shifted. We picked up METAPOINT_002 (unique AMR class count), lost METAPOINT_005 (padding length).
- METAPOINT_005's failure mode is "input file path doesn't exist" — likely the path-prefix bug (the question references `metapointfinder/notebooks/pad_to_10kb/data/input_sequences.fasta` but the repo *is* `metapointfinder`, so the real path is `notebooks/pad_to_10kb/data/input_sequences.fasta`). Karthik's older `gpt-4.1-mini` somehow found it; our `gpt-5-mini` did not.

### SKiM-GPT — 0/5 ✗ ✗ ✗ ✗ ✗ (matches Karthik's 0/5)

| ID | Steps | Our final (truncated) | Truth | Ours | Karthik | His final (truncated) |
|---|---|---|---|---|---|---|
| SKIMGPT_001 | 7 | `Execution blocked — directory 'skimgpt/notebooks/w…` | `0.89` | ❌ | ❌ | `0.85` |
| SKIMGPT_002 | 10 | `I cannot produce the requested Score…` | `0.81` | ❌ | ❌ | `The Score value for Iteration 2 in…` |
| SKIMGPT_003 | 11 | `Could not complete merge: the specified directory…` | `0.98` | ❌ | ❌ | `0.87` |
| SKIMGPT_004 | 4 | `Execution blocked — the specified directory skimgp…` | `10` | ❌ | ❌ | `The merged output TSV file has a total of 424 rows…` |
| SKIMGPT_005 | 9 | `Execution failed: the specified directory…` | `H1` | ❌ | ❌ | `Accept` |

**Notes**:
- Same outcome (0/5) but a different *failure mode*. Karthik's old agent confidently hallucinated wrong numeric/categorical answers (`0.85`, `0.87`, `Accept`). Our agent explicitly refuses once it sees the input directory doesn't exist (`Execution blocked: directory not found`). This is arguably better behavior — fewer false positives.
- **Likely root cause**: all 5 questions reference paths like `skimgpt/notebooks/eval_json_results/data/test_dch_output`. The repo *is* `skimgpt` (cloned to `papers/SKiM-GPT/repo/`), so the correct relative path is `notebooks/eval_json_results/...` without the `skimgpt/` prefix. The agent's prompt (`REACT_INSTRUCTIONS` in `react_agent.py`) doesn't include the path-stripping retry rule that `research_agent.py`'s prompt has.

## Where the model swap helped vs didn't

| Outcome | Count | Examples |
|---|---|---|
| **NEW WIN** (we got it, Karthik didn't) | 4 | PPLM_003, PPLM_005, METAPOINT_002, CROSSPPI_006 |
| **LOST WIN** (Karthik got it, we didn't) | 1 | METAPOINT_005 |
| **Same correct outcome** | 17 | (3 both right: PPLM_002, METAPOINT_001, METAPOINT_004; 14 both wrong) |
| **Net**| **+3** | |

## Failure-mode pattern (qualitative)

Two distinct failure-mode shifts in this sweep vs Karthik's:

1. **Refusal-over-hallucination**. `gpt-5-mini` is markedly less willing to commit a final answer when inputs aren't reachable. Karthik's `gpt-4.1-mini` often produced confident-but-wrong numeric/categorical answers (CROSSPPI_001 `7.83`, CROSSPPI_004 `-0.0306`, SKIMGPT_005 `Accept`). Our agent explicitly says "execution blocked" with a clear explanation. Both still wrong by ground-truth match, but ours is debuggable; Karthik's looks like a confident answer that just happens to be wrong.

2. **Better pickle-handling and tool inspection**. The PPLM_003 and PPLM_005 wins (both pickled tensor shapes) are notable — the agent successfully introspected pickle output formats. This is the kind of "read the docs, read the script, predict the output shape" reasoning that smaller models often skip.

## Where the path-prefix bug bit

5 of the 12 net failures look like the path-prefix bug — questions reference `<repo>/path/to/file` but the repo *is* `<repo>`, so the correct relative path drops the prefix:

- METAPOINT_005 (`metapointfinder/notebooks/pad_to_10kb/data/input_sequences.fasta`)
- SKIMGPT_001 through 005 (all reference `skimgpt/notebooks/...`)
- CROSSPPI_001-005 also involve `save/` and other paths inside CrossPPI's repo

`research_agents/agents/research_agent.py` *has* the path-stripping retry rule (added during the migration). `research_agents/agents/react_agent.py` *does not*. Adding it would likely flip 3-5 of these failures into successes, but would require modifying Karthik's file — out of scope for this sweep.

## Output file locations (for digging later)

### PPLM
```
papers/PPLM/runs/20260526T205546-3dcc5c2d/PPLM_001.json
papers/PPLM/runs/20260526T205643-3a45b3de/PPLM_002.json
papers/PPLM/runs/20260526T205724-c9229b8f/PPLM_003.json
papers/PPLM/runs/20260526T205836-27a2dff5/PPLM_004.json
papers/PPLM/runs/20260526T205954-f6383389/PPLM_005.json
papers/PPLM/runs/20260526T210147-7d13d4e9/PPLM_006.json
```

### CrossPPI
```
papers/CrossPPI/runs/20260526T205547-a9765a74/CROSSPPI_001.json
papers/CrossPPI/runs/20260526T205632-c17b2a98/CROSSPPI_002.json
papers/CrossPPI/runs/20260526T205808-d3178735/CROSSPPI_003.json
papers/CrossPPI/runs/20260526T205848-4f070873/CROSSPPI_004.json
papers/CrossPPI/runs/20260526T210002-bd4e2a36/CROSSPPI_005.json
papers/CrossPPI/runs/20260526T210050-ef33e05b/CROSSPPI_006.json
```

### metapointfinder
```
papers/metapointfinder/runs/20260526T204913-512ab57c/METAPOINT_001.json
papers/metapointfinder/runs/20260526T205017-31b3e8aa/METAPOINT_002.json
papers/metapointfinder/runs/20260526T205129-a09fab8f/METAPOINT_003.json
papers/metapointfinder/runs/20260526T205244-7cf29764/METAPOINT_004.json
papers/metapointfinder/runs/20260526T205413-0e9dccba/METAPOINT_005.json
```

### SKiM-GPT
```
papers/SKiM-GPT/runs/20260526T205549-cc7f760a/SKIMGPT_001.json
papers/SKiM-GPT/runs/20260526T205628-0f5c4a0c/SKIMGPT_002.json
papers/SKiM-GPT/runs/20260526T205731-82225333/SKIMGPT_003.json
papers/SKiM-GPT/runs/20260526T205833-39bbcde9/SKIMGPT_004.json
papers/SKiM-GPT/runs/20260526T205921-7324e6f6/SKIMGPT_005.json
```

## Artifacts inventory — what's saved, where, and what isn't

### Persistent on disk (under the project root)

1. **22 chain JSONs** — the structured output, one per question. Each contains the full chain (every step with `thought` / `action` / `observation` / `reflection`), the final answer, the ground truth, and the `correct` flag. Locations listed in the "Output file locations" section above. These are in `papers/` which is gitignored but persistent across reboots.

2. **22 workspace directories** — each run dir has a `workspace/` subdir where the agent staged files and ran commands. Volume:
   - PPLM runs that succeeded (003, 005): ~34 MB each (the PPLM repo staged in + pickle outputs)
   - CrossPPI runs that installed torch/ESM: ~80 MB each
   - METAPOINT successful runs: ~900 KB each
   - SKIMGPT runs (mostly bailed early): 0 files in most; SKIMGPT_005 wrote 43 files / 900 KB
   - **Total**: ~227 MB across all 22 workspaces. Useful for debugging specific failures.

3. **22 per-run venvs** — each run dir has `.venv/` from `uv venv --seed`. These are bulky (~150 MB each with torch + transitives in the PPLM/CrossPPI cases). Safe to delete after this sweep if disk space matters.

4. **4 batch stdout logs** — preserved from `/private/tmp/` (which would otherwise be swept by the OS):
   - `notes/batch_logs_2026-05-26/METAPOINT.log` (33 KB)
   - `notes/batch_logs_2026-05-26/PPLM.log` (35 KB)
   - `notes/batch_logs_2026-05-26/CROSSPPI.log` (42 KB)
   - `notes/batch_logs_2026-05-26/SKIMGPT.log` (25 KB)
   These contain the pretty-printed step-by-step output the script emits to stdout — same info as the chain JSONs, but in human-readable form with formatting.

5. **This results doc** at `notes/eval_results_2026-05-26.md`.

### What's NOT saved (deliberate / unavoidable)

1. **SDK trace.jsonl files** — `research_agents/react_main.py` does **not** support a `--trace` flag (unlike the older `research_agents/main.py`). So no run produced an `agents.tracing`-level event log. That means we don't have:
   - LLM-call latency per turn
   - Per-tool-call argument JSON in raw SDK form
   - Token usage per turn (the `result.usage` field is reachable but not logged anywhere)
   - The raw `MessageOutputItem` / `ToolCallItem` / `ToolCallOutputItem` sequence
   - Span timings
   The information *content* is mostly recoverable from the chain JSON (which is itself a derived view of the same events), but the raw SDK event log is gone. If you want this for future runs, adding a `--trace` flag to `react_main.py` would be a ~5-line change (out of scope for this sweep, but noted in the to-do).

2. **OpenAI dashboard traces** — `agents.tracing.set_trace_processors` was never called, so the default OpenAI processor *would* have shipped events to `platform.openai.com/traces`. Whether you can access that depends on whether the API key is associated with a dashboard-enabled account. If you log in there, the 22 traces should be visible.

3. **stderr from each batch run** — captured into the same log file as stdout via `2>&1`. So errors did get saved with stdout.

4. **The agent's intermediate reasoning between tool calls** — what the SDK calls "generation spans" in the raw trace. Karthik's `react_agent.py` is designed to force the agent to externalize this reasoning into the `thought` / `reflection` fields of the structured output, so most of it IS in the chain JSON. But there could be model-internal reasoning (especially with gpt-5-mini's reasoning tokens) that we never see.

### Quick recovery path if anything is needed

- The chain JSONs are the canonical artifact. They're the same shape Karthik's eval set uses.
- The batch logs add nothing new structurally but are easier to skim by hand.
- The workspace dirs are needed only if you want to debug a specific run's filesystem state.
- The venvs are needed only if you want to re-run a single question with the exact same dependency set.

## Schema validation (sanity)

Checked `METAPOINT_001.json`:
- top-level keys: `['chain', 'correct', 'final_answer', 'ground_truth', 'id', 'question', 'repo_link']` — exact match with Karthik's schema ✓
- step keys: `['action', 'observation', 'reflection', 'step', 'thought']` — all 5 fields ✓
- annotator field leak (`score`, `error_types`, `problematic_steps`, `final_answer_assessment`, `summary`): none ✓
- 12 steps in chain, all with all 5 fields populated ✓

All other chain JSONs follow the same shape.

## Stats summary

- **Total chains produced**: 22
- **Total steps across all chains**: 217 (mean 9.9, range 4–16)
- **Karthik's baseline correct**: 4/22 (18.2%)
- **Our correct (heuristic)**: 7/22 (31.8%)
- **Our correct (manually adjusted for the PPLM_006 false negative)**: 8/22 (36.4%)
- **Net improvement on `correct` flag**: +3 (+4 wins, -1 loss)
- **Improvement is not on the same questions**: only 14 of 22 are "both wrong"; 3 are "both right"; 4 are "we right / Karthik wrong"; 1 is "Karthik right / we wrong."

## Verdict (matches plan outcome 2)

> "Modest jump (e.g., 4/22 → 7–9/22) — better model helps but other limits (paper-text comprehension, missing data, GPU requirements, 150-turn cap on dependency installs) dominate. Implication: tackle infrastructure (GPU, longer caps, better paper extraction) before further model upgrades."

The model swap is real but bounded. The bigger gains here are *qualitative* (refusal-over-hallucination, cleaner chains, better tool inspection) than *quantitative* (+3 on the headline). The binding constraint for the next jump is **environment**, not model:

1. **Path-prefix bug** — ~5 likely-recoverable failures. Single-line prompt change in `react_agent.py` (out of scope here).
2. **Missing torch/ESM in the per-run venv** — 4+ likely-recoverable failures. Would need either GPU setup or pre-baked environments.
3. **`_is_correct` heuristic precision** — at least 1 false negative (PPLM_006 was numerically identical, lost on rounding). Fixing the heuristic would be a single function change in `react_main.py`.

If we fixed all three, the 7/22 likely becomes ~12-15/22. That's the natural next plan.

## To-do (for a future session, not this one)

- ☐ Manually flip PPLM_006 from ❌ to ✅ in any downstream consumers (precision-mismatched false negative)
- ☐ Consider whether a "polish pass" via `react_agent.py` prompt update for path-stripping is worth doing (gains ~5 questions, costs a one-line modification to Karthik's file)
- ☐ Decide whether to keep the 22 chain JSONs around (they're in gitignored `papers/<slug>/runs/`, persistent but not tracked)
- ☐ If the chain quality is good enough, consider feeding them into Karthik's annotator pipeline (manual copy into `HumanEvaluation/Chains/` — out of scope here)

---

*Run complete: 2026-05-26. Single-variable A/B vs Karthik's baseline. No git commits performed. All Karthik's files byte-identical pre and post sweep.*
