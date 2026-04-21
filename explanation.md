# Research Agents — Project Explanation

A walkthrough of the codebase for a newcomer who already knows ML / LLMs and is getting oriented on this specific project. Skips Python / venv / dotenv basics; focuses on the SDK integration, the agent design, and the project-specific choices.

---

## 1. What this project does

This project builds an autonomous agent that takes a research paper (PDF) plus its source repository and tries to **reproduce the paper's experiments end-to-end**. Given a question like _"Reproduce the experiments described in this paper"_, the agent reads the PDF, explores the repo, installs dependencies into an isolated Python environment, stages the relevant scripts and data into a fresh workspace, executes the experiments, reads the resulting outputs, and reports structured results that include both the numbers it actually produced and a comparison with the numbers the paper reports.

It is evaluated against [Paper2AgentBench](https://github.com/jmiao24/Paper2AgentBench) — a public benchmark of research papers with per-paper benchmark questions, some with ground-truth answers.

---

## 2. Why the OpenAI Agents SDK

We use [`openai-agents >= 0.13.6`](https://github.com/openai/openai-agents-python) (pinned in `pyproject.toml`) instead of rolling our own tool-calling loop. The relevant features:

- **First-party tool-calling loop.** `Runner.run_sync(agent, question, context=ctx)` handles the entire back-and-forth: the LLM emits a tool call, the SDK invokes the matching Python function, feeds the result back, and repeats until the model either emits structured output or hits the turn cap. We never have to implement "is there a tool call on this message?" plumbing.
- **Typed context.** Every tool receives `RunContextWrapper[ResearchContext]` as its first argument. `ResearchContext` is a dataclass that carries the resolved paths for the paper, repo, workspace, and venv — see `research_agents/project.py`. The LLM never sees these paths; they are injected at the Python layer, which keeps the prompt short and the surface area for path-traversal attacks small.
- **Native structured output.** Setting `output_type=ResearchAnswer` on the Agent makes the SDK negotiate a Pydantic schema with the model and return a validated `ResearchAnswer` instance. No brittle regex-from-JSON parsing, no manual validation.
- **Built-in turn guardrails.** `MaxTurnsExceeded` fires automatically if the agent blows past `max_turns=150`. That's exactly the semantic we want for batch benchmarking — we treat a runaway run as a failed run and exit with a non-zero code instead of trying to salvage partial output.

The alternative would have been to wire up raw Chat Completions with a hand-rolled tool loop. Given that we need all of the above, the SDK is a net reduction in our code.

---

## 3. Big-picture architecture

```
papers/<slug>/             ──►  resolve_project()  ──►  ResearchContext
  paper.pdf                                              │
  repo/                                                  ▼
  runs/<run-id>/                                    Agent (9 tools)
    workspace/   ◄──── stage/write/exec ─────────────────┤
    .venv/       ◄──── venv for this run only ───────────┤
                                                         ▼
                                                   ResearchAnswer
                                                   (Pydantic)
```

The orchestration is deliberately thin. `main.py` is a ~100-line CLI that:
1. Parses `--project` and `--question`.
2. Calls `resolve_project()` → `ResearchContext` (validates paths, mints a run ID, creates the venv).
3. Calls `create_research_agent(model=...)` → `Agent` (wires up the 9 tools and the system prompt).
4. Hands both to `Runner.run_sync()` and prints the resulting `ResearchAnswer`.

Everything else — PDF parsing, repo listing, file writing, subprocess execution — lives in `tools/` modules that get surfaced to the agent as `@function_tool` wrappers.

---

## 4. Project layout on disk

```
papers/<slug>/
  paper.pdf                        # the research paper (local)
  repo/                            # the paper's source repo (local clone)
  runs/
    <run-id>/                      # one directory per CLI invocation
      workspace/                   # agent writes here, commands run here
      .venv/                       # uv-created isolated env for this run
```

- `papers/` is **local and gitignored**. Each contributor clones the papers' repos and places the PDFs themselves. No paper or repo is committed to this project.
- `paper.pdf` — the research paper. Opened with `pypdf.PdfReader` for text extraction; figures and image-only pages are lost (see section 6).
- `repo/` — the paper's source repository, treated as **input-only**. The agent reads from it via `list_repo_files` / `search_repo` / `read_repo_file`, and stages files into the workspace via `stage_repo_path`. Nothing the agent does ever writes to `repo/`.
- `runs/<run-id>/` — created fresh on every CLI invocation. `<run-id>` is `<UTC-timestamp>-<uuid8>` (e.g. `20260421T143022-a1b2c3d4`), so runs sort chronologically and never collide.
- `runs/<run-id>/workspace/` — the agent's CWD. Everything it writes via `write_file` or stages via `stage_repo_path` goes here.
- `runs/<run-id>/.venv/` — the run-scoped Python environment. Created lazily on first `resolve_project` call via `uv venv --seed`; re-used if the directory already exists.

**Worked example.** Running the CLI against `papers/sam2` kicks off:
```
papers/sam2/
  paper.pdf                               # Ravi et al. 2024
  repo/                                   # facebookresearch/sam2 clone
  runs/
    20260421T143022-a1b2c3d4/             # fresh every run
      workspace/
        predictions.csv                   # written by the agent
        run_inference.py                  # written by the agent
      .venv/                              # has torch, sam2, ... pip-installed
```

---

## 5. Configuration & models

`research_agents/config.py` exposes two model IDs matching what our API key has access to:

| Constant | Model | Role |
|----------|-------|------|
| `DEFAULT_MODEL` | `gpt-4.1-mini-2025-04-14` | Cheaper / faster. Default choice for development and simple questions. |
| `ALTERNATE_MODEL` | `gpt-5-mini-2025-08-07` | Stronger reasoning. Pick via `--model` for involved multi-experiment reproductions or long, dense repos. |

Both models expose the same tool-calling and structured-output interface, so they are drop-in interchangeable. The practical rule of thumb from benchmarking: use `gpt-4.1-mini` for iteration, switch to `gpt-5-mini` when a `gpt-4.1-mini` run fails in a way that looks like a reasoning gap (e.g. wrong file paths, missed experiments) rather than an environmental gap (e.g. missing weights, timeout).

`max_turns=150` is set in `main.py`. Most successful runs finish in 30–80 turns; 150 leaves enough headroom for the few experiments that need many retries while still catching a genuinely stuck agent.

---

## 6. The 9 tools

All tools live under `research_agents/tools/`. Each is a thin `@function_tool` wrapper over a pure Python function that is also unit-tested directly.

### Reading tools (4)

| Tool | Purpose | Key limits |
|------|---------|------------|
| `read_paper` | Extract text from `paper.pdf` via `pypdf`. One-shot; the agent reads the whole paper in a single tool call. | Images / figures / scanned pages dropped. |
| `list_repo_files` | List every readable text file under `repo/`. Ignores `.git`, `.venv`, `node_modules`, build artifacts, and binary files. | `MAX_LISTED_FILES = 400` |
| `search_repo` | Case-insensitive grep across readable repo files. | `MAX_MATCHES = 50`, `MAX_LINE_LENGTH = 240` preview |
| `read_repo_file` | Read one text file from `repo/` by relative path. Rejects path-traversal (`../..`), binary files, and files bigger than 200 KB. | `MAX_FILE_BYTES = 200_000` |

### Execution tools (5)

| Tool | Purpose | Key limits |
|------|---------|------------|
| `write_file` | Create / overwrite a file under `workspace/`. Rejects absolute paths and path-traversal. | `MAX_WRITE_BYTES = 500_000` |
| `stage_repo_path` | Copy a file or directory from `repo/` into `workspace/` so commands can read and modify it. Skips ignored dirs. | — |
| `execute_command` | Run a shell command from `workspace/`. `shell=True` (pipes and redirects work); PATH starts with the run's venv; `PYTHONPATH` starts with the repo root. | `DEFAULT_TIMEOUT = 120s`, `MAX_TIMEOUT = 600s`, output capped at `MAX_OUTPUT_BYTES = 50_000` |
| `list_workspace_files` | Walk `workspace/` and report everything the agent has written. | `MAX_LISTED_FILES = 400` |
| `read_workspace_file` | Read a workspace file (CSVs, logs, JSON outputs). | `MAX_READ_BYTES = 200_000` |

Design rules enforced by these tools:
- **`repo/` is input-only.** Only `stage_repo_path` can copy out of it; nothing writes into it.
- **Every path is sandboxed.** Paths are resolved and then checked against the expected root; a request with `../../etc/passwd` gets a clean `ValueError` instead of leaking the filesystem.
- **Sizes are capped.** Every tool truncates or rejects oversized input/output so one rogue log file cannot blow the LLM's context window.

---

## 7. The 6-phase workflow

Paraphrased from the `INSTRUCTIONS` prompt in `research_agents/agents/research_agent.py`:

1. **UNDERSTAND** — Read the question. Call `read_paper`. Use `list_repo_files`, `search_repo`, and `read_repo_file` to map the methodology, available data, and how the scripts are meant to run. For a read-only question, jump to phase 6.
2. **PLAN** — Enumerate every experiment in the paper (tables, figures, ablations, baselines). Map each to the files that implement it. Mark infeasible ones (missing weights, GPU required, gated data) and explain why. Order feasible experiments so shared setup runs once. Plan the exact commands.
3. **SETUP** — Install dependencies into the run's venv (`pip install ...` routes there automatically). Use `stage_repo_path` to copy scripts and data into the workspace. Use `write_file` for helpers or wrappers. `RESEARCH_*` env vars plus the repo-on-PYTHONPATH let staged scripts find what they need.
4. **EXECUTE** — Run one experiment at a time. After each command, inspect any output files. Retry failures up to 5× per experiment; after that, record the failure and continue. Crucially: _do not abandon the run on the first blocker_. If one experiment is gated and another isn't, run the unblocked one.
5. **INTERPRET** — Read stdout and output files for each successful experiment. Extract quantitative results. Compare each against the paper-reported value. Synthesize across experiments if there were several.
6. **REPORT** — Emit a `ResearchAnswer` with a top-level summary, per-experiment `ExperimentResult` records (successes AND failures), and a reproducibility assessment.

The prompt also forbids two failure modes that are easy for an LLM to fall into: **copying paper-reported numbers into `key_findings`** (so the agent looks productive even when it didn't run anything) and **dropping failed experiments** (so the results look better than reality).

---

## 8. The venv-per-run story

The single most project-specific design decision is: **every CLI invocation gets its own Python virtual environment**.

Why:
- **Cross-paper isolation.** Torch 2.0 for one paper, torch 2.3 for another — we can't share one venv across papers without constant conflict storms.
- **Cross-run isolation.** A botched `pip install` in one run doesn't poison the next run against the same paper.
- **System hygiene.** The host Python is never touched. Users don't have to trust a shared project env.

How:
- `research_agents/project.py :: _ensure_venv` runs `uv venv --seed <venv_path>` on first use. `--seed` pre-installs pip/setuptools so the agent's first `pip install` call works without bootstrap.
- The venv lives at `papers/<slug>/runs/<run-id>/.venv/`. If it already exists (e.g. the run directory was inspected and re-opened), creation is skipped. The check handles both the Unix `bin/python` and Windows `Scripts/python.exe` layouts.
- `research_agents/tools/exec_tools.py :: execute_command_text` prepends the venv's `bin/` directory to `PATH` and sets `VIRTUAL_ENV` before running each subprocess. Result: the agent writes plain `python foo.py` and `pip install bar`, and those commands resolve into the isolated env without the LLM ever having to know the absolute path. That's why the system prompt tells the agent _"never use system python or pip directly — they are already routed to the project venv"_.

---

## 9. Structured output

The agent's final message is a `ResearchAnswer` Pydantic model (`research_agents/agents/research_agent.py`). Top-level fields:

| Field | Type | Role |
|-------|------|------|
| `answer` | `str` | Executive summary of what the agent did and found. |
| `reasoning` | `str` | Detailed reasoning referencing paper sections and repo files. |
| `sources` | `list[str]` | Paper path plus the repo / workspace files that back the reasoning. |
| `experiments` | `list[ExperimentResult]` | One per attempted experiment. Empty for a purely read-only question. |
| `overall_interpretation` | `str \| None` | Cross-experiment synthesis when several ran. |
| `reproducibility_assessment` | `str \| None` | Overall judgment on how well the paper was reproduced. |

And one `ExperimentResult` per attempted experiment:

| Field | Role |
|-------|------|
| `name` | Short human-readable label. |
| `paper_reference` | Where in the paper this experiment is defined (e.g. "Section 4.2, Table 1"). |
| `scripts_used` | Scripts invoked — repo scripts or agent-written helpers. |
| `commands_run` | Full shell commands, for human-reproducibility. |
| `success` | `True` only if execution produced usable results. |
| `key_findings` | Numbers the agent actually produced. Paper-reported numbers do **not** belong here. |
| `output_files` | Files produced in `workspace/`; defaults to empty for experiments that print to stdout only. |
| `interpretation` | What the findings mean relative to the paper's claim. |
| `paper_comparison` | Optional. Side-by-side with the paper's reported value. |
| `error_summary` | Optional. Describes the blocker when `success=False`. |
| `attempts` | Total execution attempts the agent made for this experiment before giving up or succeeding. Default 1; the agent writes the final count after any retries. |

Two invariants enforced by the prompt:
- **Failed experiments get their own record.** They are data about what's blocked and why.
- **Paper-reported numbers are never copied into findings.** If the agent could not run an experiment, `success=False` and `key_findings` stays empty — it does not inherit the paper's claim.

---

## 10. Test suite overview

3 files, 45 tests, all green on macOS/Python 3.12. No live network, no LLM calls — everything is pure functions over tmp dirs.

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_repo_tools.py` | list / search / read / schema | Text-vs-binary detection, ignored dir pruning, size cap, path-traversal rejection, `ResearchContext` path hiding from tool schemas, PDF extraction, empty-PDF rejection. |
| `tests/test_project.py` | 4 tests | `resolve_project` creates a fresh run ID per call, validates paper + repo presence, rejects missing / non-dir project paths. |
| `tests/test_exec_tools.py` | write / stage / execute / list / read | venv routing (python resolves into the run venv), timeout behavior, output truncation, RESEARCH_* env vars, path-traversal rejection, size caps. |

**Gaps worth knowing about** (not covered today, deliberate):
- **No integration tests.** The agent is never actually booted with a real LLM in CI; we test the tools as pure functions.
- **No agent-behavior tests.** There is no test that says "for this question, the agent should produce exactly these tool calls." Those are brittle and expensive.
- **No automated bench grading.** The Paper2AgentBench compbio set ships a `ground_truth` column but we currently eyeball-grade rather than auto-diff.

---

## 11. Evaluation corpus

Paper2AgentBench ships two CSVs that drive our testing (links in the README):

- `eval/5_nonbio_repos/17_questions.csv` — 17 questions across 5 non-bio papers (grf, tabpfn, sam2, saelens, binoculars). **No `ground_truth` column** — manual grading.
- `eval/100_compbio_repos/300_questions.csv` — 300 questions across 100 compbio papers, paired with `100_papers_link.csv` (bioRxiv DOIs). **Has a `ground_truth` column**, so compbio runs can eventually be scored automatically.

Locally we have two compbio examples set up end-to-end under `papers/`: `segma` (from Paper2AgentBench) and `medchem` (a local-only example — not part of the 100-paper corpus). The 5 non-bio papers are all in `papers/` too. See the README for paper / repo links.

---

## 12. Current bench results (34 runs)

Most recent full sweep: 17 non-bio questions × 2 models = **34 runs**.

**Aggregate:** 2 full successes, 3 partial successes, 29 runs that did not produce paper-relevant execution.

### By question (summary)

| Q | Repo | Outcome summary |
|---|------|-----------------|
| Q01, Q03, Q04, Q09, Q10, Q11, Q14, Q16, Q17 | grf | All grf runs on both models: agent ran `notebooks/foo.ipynb` with the literal `grf/` prefix from the question (repo root IS grf, actual path is `notebooks/foo.ipynb`). No execution. Secondary blocker: no R interpreter in the venv. |
| Q02, Q08 | saelens | No execution — agent did not locate an end-to-end runnable experiment script; SAE training would have hit the 600s ceiling anyway. |
| Q05, Q13 | tabpfn | Partial (3 runs): agent substituted sklearn baselines in place of the license-gated TabPFN weights. Sklearn results logged; TabPFN proper never ran. |
| Q06 | sam2 | **Full success (gpt-5-mini only):** "cars" segmentation reproduced from the repo example. `gpt-4.1-mini` version failed at dependency resolution. |
| Q07 | sam2 | **Full success (both models):** "groceries" segmentation; matches the paper's qualitative claim. |
| Q12, Q15 | binoculars | No execution — agent answered the detector-vs-stylistic question from the paper text and never invoked the Binoculars script. |

### Key takeaways

- **grf was sunk by a prompt-path ambiguity.** The question says `grf/notebooks/xyz`, but our `repo/` root IS `grf`. Neither model stripped the prefix. Adding either a small "assume paths are relative to `repo/`" note to the instructions or a bit of defensive retry logic in the agent would likely unblock most of these.
- **sam2 is the most credible win.** Two full successes, one on each model, with matching qualitative output. Suggests the pipeline is working when the repo provides a self-contained example.
- **TabPFN partials are actually informative.** Running sklearn baselines when TabPFN is license-gated is exactly the behaviour the prompt asks for: don't abandon the run, do what's feasible. We got useful comparison numbers.
- **saelens + binoculars both show "skip execution when the path isn't obvious."** That's the same failure mode in different clothes — both repos bury the runnable example deep, and both models answered from the paper text without trying to execute. A "PLAN phase must end with at least one concrete `python <script>` command" nudge would probably help.
- **Single-command budget ceilings hurt.** SAE training is minutes-to-hours even in toy form; we capped at 600s. An explicit "skip training, demo inference only" instruction in the prompt would let saelens land at least a partial.

---

## 13. Known limitations

Merging the README's list with fresh observations from the latest benchmark:

- **Fixed local layout.** Each project must be `papers/<slug>/` with exactly `paper.pdf` and `repo/`. No discovery of alternate layouts.
- **Text-only PDF extraction.** Figures, tables rendered as images, and scanned pages are invisible to the agent.
- **No GPU in the venv.** `uv venv --seed` doesn't install CUDA stacks; large-model training scripts tend to fail at import time. Working around this per-paper is possible but unautomated.
- **No R interpreter.** Several grf notebooks are R, which the default Python venv can't run. Adding R would be a semi-architectural change — deferred.
- **`grf/`-prefix bug in Paper2AgentBench questions.** Questions paste paths as `grf/notebooks/...`; our repo root IS `grf`. Both models executed them literally. Not patched in this pass; noted as a known failure mode.
- **Binoculars "stylistic vs. detector" trap.** When asked to judge whether a text is AI-generated, both models answered from the paper description instead of invoking the Binoculars detector. The prompt should probably explicitly require running the detector when available.
- **License-gated model weights.** TabPFN proper needs a gated download. Our runs degrade gracefully to sklearn baselines; the gated run never happens.
- **CUDA-gated experiments.** Anything requiring `cuda.is_available()` just can't run here.
- **600s per-command ceiling.** SAE training and other minutes-to-hours workloads exceed it.
- **Non-bio benchmark has no `ground_truth` column.** Grading is manual. The compbio set has ground truths we haven't wired up auto-grading for yet.
- **`read_repo_file` fails on directory paths.** Known bug: if the agent passes a path that happens to be a directory, the tool raises a confusing error. Scoped for a future pass.

---

## 14. One-page summary

Drop-in bullets for a slide:

- **Purpose:** autonomous agent that reads a paper + its repo and reproduces the paper's experiments end-to-end.
- **SDK:** OpenAI Agents SDK (`openai-agents >= 0.13.6`) — first-party tool-calling loop, typed `RunContextWrapper[ResearchContext]`, Pydantic structured output via `output_type=ResearchAnswer`, built-in `MaxTurnsExceeded` guardrail.
- **Models:** `gpt-4.1-mini-2025-04-14` (default — cheap) and `gpt-5-mini-2025-08-07` (alternate — stronger reasoning). `max_turns=150`.
- **9 tools in 2 groups:** 4 reading (`read_paper`, `list_repo_files`, `search_repo`, `read_repo_file`); 5 execution (`write_file`, `stage_repo_path`, `execute_command`, `list_workspace_files`, `read_workspace_file`).
- **6-phase workflow:** UNDERSTAND → PLAN → SETUP → EXECUTE → INTERPRET → REPORT.
- **Venv per run:** every CLI invocation gets a fresh `uv venv --seed` at `papers/<slug>/runs/<run-id>/.venv/`; `execute_command` prepends its `bin/` to `PATH` and repo root to `PYTHONPATH`, so bare `python` / `pip install` Just Work.
- **Structured output:** `ResearchAnswer` (answer, reasoning, sources, experiments, overall interpretation, reproducibility assessment) + `ExperimentResult` per experiment (paper reference, commands, findings, error summary, attempts). Failed experiments get their own record; paper-reported numbers never copied into findings.
- **Tests:** 45 tests in 3 files — tools, project resolution, exec sandbox. No live-LLM integration tests yet.
- **Current status (17 non-bio × 2 models = 34 runs):** 2 full successes (sam2 groceries + cars), 3 partials (sklearn stand-ins for gated TabPFN), 29 no-execution.
- **Works:** sam2-style repos that ship a self-contained runnable example.
- **Fails:** path-prefix mismatch (grf), no R, license gates (TabPFN weights), detector-vs-stylistic confusion (Binoculars), 600s training ceiling (SAELens).
- **Biggest challenges going forward:** (1) path-prefix heuristic or defensive retry in the PLAN phase, (2) a rule that forces the agent to run the paper's code when available, (3) auto-grading against the compbio `ground_truth` column, (4) GPU + R environments.
