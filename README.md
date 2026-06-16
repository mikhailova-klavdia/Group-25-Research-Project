# Research Agents

Research agents powered by the OpenAI Agents SDK for analyzing local paper + repository projects.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key with access to `gpt-4.1-mini` or `gpt-5-mini`

## Setup

```bash
# Clone the repo
git clone <repo-url>
cd Group-25-Research-Project

# Clone Paper2AgentBench into the repo root
git clone https://github.com/jmiao24/Paper2AgentBench

# Create your .env file with your API key
cp .env.example .env
# Edit .env and add your actual OPENAI_API_KEY

# Install dependencies
uv sync
```

`Paper2AgentBench/` is a local benchmark data dependency. Keep it cloned at the repository root so paths like `Paper2AgentBench/eval/100_compbio_repos/300_questions.csv` resolve correctly.

## Project Layout

Create a local workspace under `papers/` for each paper you want to analyze:

```text
papers/<project-slug>/
  paper.pdf        # the research paper
  repo/            # cloned repository for the paper
  .research_config.toml  # optional paper-specific venv settings
  .venv/           # auto-created shared Python environment for this paper
  costs.json       # optional accumulated token/cost log
  runs/
    <run-id>/
      workspace/   # auto-created fresh workspace for this run
```

- `paper.pdf` is the local paper file.
- `repo/` is the full checked-out repository associated with that paper.
- `runs/<run-id>/workspace/` is auto-created on every CLI run. Agent-generated scripts and outputs live there.
- `.venv/` is a shared per-paper Python environment. Dependencies installed for one question are reused by later questions for the same paper.
- `.research_config.toml` can pin a paper-specific venv Python version and seed packages:

```toml
[venv]
python_version = "3.9"
seed_packages = ["torch==1.13.1"]
```

- `repo/` is shared across runs and treated as input-only. The agent reads from it and stages files into the run workspace before execution.
- `papers/` is a local workspace and is ignored by git.
- Any local corpus under `papers/<slug>/` (Paper2AgentBench non-bio and compbio picks, plus local examples) is workspace data, not tracked repository contents.

## Setting Up Your Papers Folder

`Papers/` (capital P) is the local folder where you keep the 74 compbio repos you want to evaluate. It is gitignored — each contributor populates it locally. Each subfolder must follow this layout:

```text
Papers/<tagged-folder-name>/
  biorxiv_link.txt   # single line: full biorxiv URL e.g. https://www.biorxiv.org/content/10.1101/...v1
  paper.pdf          # the paper PDF (gitignored via *.pdf)
  repo/              # cloned GitHub repository for this paper
```

### Folder naming scheme

Folders use a structured name so they sort by runnability and carry machine-readable tags:

```
<rank>-<papernum><difficulty><tags>-<name>
```

| Part | Meaning |
|------|---------|
| `rank` | Two-digit sort order (01 = most runnable, 74 = least) |
| `papernum` | Original paper index (1–74) |
| `difficulty` | `E` easy · `M` medium · `H` hard (based on env setup clarity) |
| `tags` | Zero or more single-letter issue tags immediately after difficulty |
| `name` | Human-readable repo name |

**Issue tags:**

| Tag | Issue | Effect on the pipeline |
|-----|-------|------------------------|
| `r` | R language repo | Python/uv env agent fails at step 1 |
| `c` | Compiled / conda-only / bioconda | `uv` cannot install it |
| `n` | No tutorials or notebooks found | Pipeline stalls after env setup |
| `g` | GPU required | Tutorial execution crashes without CUDA |
| `d` | Data download needed | Tutorial crashes on missing files |
| `a` | API key needed at runtime | Calls fail without key |
| `w` | Pretrained weights needed | Model fails to load |
| `k` | Docker / container only | Nothing runs outside container |

Tags combine: `wgd` = weights + GPU + data all needed. The full index with per-repo notes is in [`papertags.md`](papertags.md).

**Examples:**

```
01-3M-CyteOnto                          # rank 1, paper 3, Medium, no blockers
32-64Mgd-augment-finetune-genomics      # rank 32, paper 64, Medium, needs GPU + data
74-73Hwgd-PPLM                          # rank 74, paper 73, Hard, weights + GPU + data
```

### Tagging your own Papers folder with Claude

If you are setting up a fresh `Papers/` folder, you can ask Claude Code to analyse and tag it automatically. Open Claude Code at the project root and paste:

```
I have a Papers/ folder with research repos. For each subfolder:
1. Check for pyproject.toml, requirements.txt, setup.py, environment.yml, Dockerfile, DESCRIPTION (R). Note what's there.
2. Grep for "wget", "curl", "download", "checkpoint", "pretrained", "huggingface", "gdown", "zenodo" to detect weight/data downloads.
3. Check for GPU/CUDA mentions.
4. Look for Jupyter notebooks or README tutorial sections.
5. Classify each repo:
   - Difficulty: E (clear setup), M (ambiguous), H (agent cannot automate)
   - Tags: r (R language), c (compiled/conda-only), n (no tutorials), g (GPU), d (data download), a (API key), w (weights), k (Docker only)
6. Assign ranks 01–N, lowest rank = most automatable (clean Python + PyPI + has tutorials + no blockers).
7. Rename every folder to <rank>-<papernum><difficulty><tags>-<name>.
8. Write a papertags.md at the project root documenting the scheme and full index.
```

Claude will analyse all repos, rename the folders, and produce `papertags.md`. Ranks 01–21 (approximately) should be fully runnable by `run_eval.py` without manual intervention.

## Evaluation Corpus

The agent is tested against a local `papers/<slug>/` workspace per paper. `papers/` is gitignored — contributors clone the repos and download the PDFs locally. Benchmark questions and (where available) ground truths come from [Paper2AgentBench](https://github.com/jmiao24/Paper2AgentBench), which should be cloned locally into `./Paper2AgentBench/`:

```bash
git clone https://github.com/jmiao24/Paper2AgentBench
```

| Bench set | Questions | Paper / repo mapping | Ground truth |
|-----------|-----------|----------------------|--------------|
| Non-bio | [`5_nonbio_repos/17_questions.csv`](https://github.com/jmiao24/Paper2AgentBench/blob/main/eval/5_nonbio_repos/17_questions.csv) | `github_link` column | Manual grading |
| Compbio | [`100_compbio_repos/300_questions.csv`](https://github.com/jmiao24/Paper2AgentBench/blob/main/eval/100_compbio_repos/300_questions.csv) | [`100_compbio_repos/100_papers_link.csv`](https://github.com/jmiao24/Paper2AgentBench/blob/main/eval/100_compbio_repos/100_papers_link.csv) (bioRxiv DOIs) | `ground_truth` column |

### Non-bio test set (papers present locally)

| Slug | Paper | Repo |
|------|-------|------|
| `grf` | [Generalized Random Forests (Athey, Tibshirani, Wager — arxiv 1610.01271)](https://arxiv.org/abs/1610.01271) | [grf-labs/grf](https://github.com/grf-labs/grf) |
| `tabpfn` | [Accurate predictions on small data with a tabular foundation model (Hollmann et al., Nature 2025)](https://doi.org/10.1038/s41586-024-08328-6) | [PriorLabs/TabPFN](https://github.com/PriorLabs/TabPFN) |
| `sam2` | [SAM 2: Segment Anything in Images and Videos (Ravi et al., arxiv 2408.00714)](https://arxiv.org/abs/2408.00714) | [facebookresearch/sam2](https://github.com/facebookresearch/sam2) |
| `saelens` | [Sparse Autoencoders Find Highly Interpretable Features in Language Models (Cunningham et al., arxiv 2309.08600)](https://arxiv.org/abs/2309.08600)¹ | [decoderesearch/SAELens](https://github.com/decoderesearch/SAELens) |
| `binoculars` | [Spotting LLMs With Binoculars (Hans et al., arxiv 2401.12070)](https://arxiv.org/abs/2401.12070) | [ahans30/Binoculars](https://github.com/ahans30/Binoculars) |

¹ SAELens itself has no standalone academic paper — its README self-cites the codebase. The linked Cunningham et al. paper is the foundational SAE-interpretability work the library is built around.

### Compbio test set (papers present locally)

| Slug | Paper (bioRxiv) | Repo |
|------|-----------------|------|
| `segma` | [10.1101/2025.11.13.688364](https://doi.org/10.1101/2025.11.13.688364) | clone per `papers/segma/repo/` remote |
| `medchem` | local example — not part of Paper2AgentBench's 100 compbio corpus | [datamol-io/medchem](https://github.com/datamol-io/medchem) |

The compbio `300_questions.csv` carries a `ground_truth` column, so compbio runs can be graded automatically.

## Usage

Ask a question about a paper (no execution):

```bash
uv run python -m research_agents.main \
  --project papers/segma \
  --question "What is the main contribution of this paper?"
```

Reproduce all feasible experiments from a paper:

```bash
uv run python -m research_agents.main \
  --project papers/segma \
  --question "Reproduce the experiments described in this paper. Run every feasible script, interpret the results, and compare with the paper."
```

Ask the agent to create and run a new script:

```bash
uv run python -m research_agents.main \
  --project papers/segma \
  --question "Write a Python script that reads test.fasta from the repo, counts sequences, and prints their average length."
```

To use a different model:

```bash
uv run python -m research_agents.main \
  --project papers/medchem \
  --question "Explore the repository and describe what modules are available." \
  --model gpt-5-mini-2025-08-07
```

## Walkthrough: Running a Paper2AgentBench question end-to-end

The example below runs an entire Paper2AgentBench non-bio question — `sam2` Q07 (`cars.jpg`) — from a cold workspace. The agent downloads the `sam2.1_hiera_large` checkpoint, installs the SAM 2 package in editable mode so its Hydra configs register, and produces 54 binary mask PNGs plus a colored overlay. This is one of the reproductions that succeeded fully in our benchmark runs.

**Prerequisite**: clone `facebookresearch/sam2` to `papers/sam2/repo/` and place the SAM 2 paper at `papers/sam2/paper.pdf`.

**Exact command** (verbatim Paper2AgentBench question, `gpt-5-mini-2025-08-07` model):

```bash
uv run python -m research_agents.main \
  --project papers/sam2 \
  --model gpt-5-mini-2025-08-07 \
  --question "Use sam2.1_hiera_large checkpoint to generate masks on the image 'https://github.com/facebookresearch/sam2/blob/main/notebooks/images/cars.jpg'"
```

**Why `gpt-5-mini-2025-08-07` and not the default**: SAM 2 registers its Hydra configs only after `pip install -e .` on the repo. On a CPU-only machine, only the stronger model consistently discovered this workaround; the default `gpt-4.1-mini` variant failed to route around CUDA-assumption errors in `build_sam2()` during our runs.

**What the agent actually does during a successful run**:

1. Reads `paper.pdf` and explores the repo (`list_repo_files`, `read_repo_file README.md`, `search_repo "sam2.1_hiera_large"`).
2. Stages `checkpoints/download_ckpts.sh` and `sam2/` into the run workspace.
3. Installs dependencies in the per-run venv: `pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu`, `pip install hydra-core omegaconf tqdm numpy pillow requests`.
4. Downloads checkpoints with `bash checkpoints/download_ckpts.sh` (~1.5 GB total across tiny/small/base_plus/large).
5. Runs `pip install -e .` so SAM 2's Hydra config search path resolves.
6. Writes a short `run_amg.py` that downloads `cars.jpg`, builds `sam2.1_hiera_l.yaml` + the large checkpoint, runs `SAM2AutomaticMaskGenerator`, and saves each mask as a PNG plus a colored overlay.
7. Executes the script, producing `workspace/amg_output/mask_000.png` … `mask_053.png` and `workspace/amg_output/overlay.png`.

**Expected outcome** (what success looks like):

- `runs/<run-id>/workspace/amg_output/` contains **54 binary mask PNGs** (`mask_000.png` through `mask_053.png`) plus a single **`overlay.png`** composite.
- The agent's structured `ResearchAnswer` reports one `ExperimentResult` with `success=true`, `output_files` listing the mask directory, and a `findings` entry noting the mask count.

**Grading note**: Paper2AgentBench's non-bio `17_questions.csv` has **no `ground_truth` column** — the expected outcome is qualitative (did the pipeline produce valid masks at all?). The compbio `300_questions.csv` does carry ground truths, which is why automated grading is only feasible on that subset.

## Paper2AgentBench Experiment Commands

The compbio chains in `question-answers/` can be run with the commands below. The default team is `solo`; pass `--team` to select a stronger team. With no `--model` flag, runs use `gpt-4.1-mini-2025-04-14`. The worker is allowed up to **150 turns** per attempt, and the critic gets a separate 10-turn review budget.

```bash
uv run python -m research_agents.react_main \
    --project papers/PPLM \
    --questions-file question-answers/PPLM.json \
    --team worker-critic-plus-plus

uv run python -m research_agents.react_main \
    --project papers/CrossPPI \
    --questions-file question-answers/CROSSPPI.json \
    --team worker-critic-plus-plus

uv run python -m research_agents.react_main \
    --project papers/metapointfinder \
    --questions-file question-answers/METAPOINT.json \
    --team worker-critic-plus-plus
```

**Full parameter summary for these runs:**

| Parameter | Value |
|-----------|-------|
| Model | `gpt-4.1-mini-2025-04-14` (default — no `--model` flag passed) |
| Max turns | 150 worker turns per attempt, 10 critic turns |
| Questions per repo | 6 / 5 / 4 working (PPLM / metapointfinder / CrossPPI) |
| Isolation | Fresh workspace per question, shared `.venv/` per paper |
| BioRxiv URL | not supplied (`repo_link: ""` in all output files) |

Each question generates one JSON file under `papers/<slug>/runs/<run-id>/<ID>.json` with the full ReAct chain (thought / action / observation / reflection per step), final answer, heuristic `correct` flag, token usage, and any `critic_reviews` / dependency `install_events`.

## Batch Evaluation with run_eval.py

Instead of calling `react_main` once per repo manually, use `run_eval.py` to run any range of ranked repos automatically. It resolves each rank to the right `Papers/` folder, matches questions from `benchmark_42.csv` via the `biorxiv_link.txt`, wires up the `papers/<slug>/` workspace, and calls `react_main` sequentially.

### Usage

```bash
# Run all 21 fully-automatable repos
uv run python run_eval.py --repos 1-21

# Run specific ranks
uv run python run_eval.py --repos 1 3 7

# Mix of ranges and singles, with model override
uv run python run_eval.py --repos 1-5 8 --model gpt-5-mini-2025-08-07
```

### What it does per repo

1. Finds `Papers/<rank>-…/` from the rank number
2. Reads `biorxiv_link.txt` and normalises the URL (strips `v1`/`v2` suffixes)
3. Scans `Paper2AgentBench/eval/100_compbio_repos/300_questions.csv` for all matching questions
4. Creates `papers/<slug>/` with a junction/symlink to `repo/` and `paper.pdf` — no data duplication
5. Writes `question-answers/<slug>.json` in the standard `[{id, question, ground_truth}]` format
6. Runs `react_main`; if it exits non-zero the warning is logged and the next repo starts

Matching and workspace setup together take under a second. The agent itself takes **5–15 minutes per question**, so 1–21 with ~3 questions each runs in roughly **5–15 hours** end-to-end.

### Timing note for `.research_config.toml`

For ranks 01–21 (clean Python/PyPI repos) no config file is needed — the agent installs dependencies live during its ReAct loop. If after a run you spot a venv failure in the chain-of-thought output, drop a `.research_config.toml` into `papers/<slug>/` to pin the Python version, seed packages, or download scripts, then delete `.venv/` and re-run so the config takes effect.

```toml
# papers/<slug>/.research_config.toml
[venv]
python_version = "3.10"
seed_packages = ["torch==2.0.1"]

[setup]
download_scripts = ["weights/download.sh"]
```

See `research_agents/project.py` (`_read_paper_config`, `_ensure_venv`, `_run_setup_scripts`) for full config reference.

## Available Models

| Model | Description |
|-------|-------------|
| `gpt-4.1-mini-2025-04-14` | Default. Faster and cheaper for development. |
| `gpt-5-mini-2025-08-07` | More capable. Use for complex analysis. |

## Independent Chain Evaluation (LLM-as-Judge)

`prompts/claude_evaluator.md` contains a self-contained prompt to run in a fresh Claude Code
session. It independently attempts all 22 questions, compares its answers against the stored
GPT-4.1-mini chains, categorises errors per chain, produces a frequency table, inspects the
OpenAI Agents SDK for structural failure causes, and outputs a `claude_annotations.json` file
in the same format as the human annotator templates (score 1–4, error\_types, problematic\_steps,
final\_answer\_assessment, summary). Re-run at the start of each iteration to get updated
diagnostics. Report written to `ClaudeEval/report.md` and annotations to `ClaudeEval/annotations.json`
at the repo root (`ClaudeEval/` is gitignored). The annotations file uses the same schema
as the human annotator templates so all four annotators (Sapan, Mihaela, Klaudia, Claude)
can be compared directly for Cohen's kappa.

## Agent Teams

All teams are selectable via `--team` on `react_main`. Nine teams ship:

| Team | Description |
|------|-------------|
| `solo` | Single ReAct worker, no critic, no install retry. Legacy `--no-critic` path. |
| `worker-critic` | Worker + LLM critic with deterministic missing-module install retry. |
| `worker-critic-plus` | Same as worker-critic but with the improved-variant prompt and up-front venv setup scripts (model-weight downloads). |
| `worker-critic-plus-plus` | Same shape as worker-critic-plus with the plus-plus prompt: repo-first search, static-file gate before execution, mandatory second-strategy rule before giving up. |
| `worker-verifier-critic` | Three agents: worker → code verifier → critic. The verifier re-checks the answer (plausibility + a known-bug checklist + an independent re-computation) and, on a fixable bug, rewrites and re-runs the script so the corrected answer reaches the critic. |
| `testing-worker-critic` | Five stages: an extraction agent inventories paper/repo workflows → a workflow-testing agent smoke-validates them → an execution worker answers from both reports → the critic audits → a gap-detection agent summarizes paper/repo/execution discrepancies. |
| `worker-env-critic` | Three agents: a dedicated Environment agent (discovers dependency files, installs packages, verifies imports → `EnvironmentReport`) → plus-plus worker (receives the report as a preamble) → critic. |
| `human-in-the-loop` | Three-stage pipeline (triage → setup → execution). A setup engineer prepares the venv interactively and calls `ask_human` when blocked. YOU answer at the terminal. Use via `hitl_main`. |
| `worker-critic-plus-plus-hitl` | Plus-plus team with a Claude operator channel: `ask_human` calls are answered by Claude autonomously in batch. Also works interactively via `hitl_main`. Requires `ANTHROPIC_API_KEY`. |

### Interactive HITL session (hitl_main)

`hitl_main` is a conversational chat REPL for the two HITL-capable teams. A lightweight **gateway LLM** handles the conversation — you can greet it, ask follow-up questions, or say thanks and it replies naturally. When you have a real research question it routes to the full pipeline (triage → setup → execution), streams live progress, asks YOU inline when stuck, and prints a clean answer.

```bash
# Default: you answer any ask_human prompts at the terminal
uv run python -m research_agents.hitl_main --project papers/<slug>

# Claude answers ask_human autonomously (requires ANTHROPIC_API_KEY)
uv run python -m research_agents.hitl_main --project papers/<slug> --team worker-critic-plus-plus-hitl

# Full reasoning-chain dump while it runs
uv run python -m research_agents.hitl_main --project papers/<slug> --verbose
```

**Example session:**

```
you> hi
agent> Hello! I'm ready to help with CrossPPI. Ask me a question about the paper or its code.

you> who r u
agent> I'm a research agent set up for CrossPPI. Ask me something specific and I'll investigate.

you> what auroc does the model get on human PPIs?
▸ Deciding how to approach your question (repo already explored)…
▸ Running it…
▸ Done.
══════════════════════════════════════════════════════════════════════
✓  The reported AUROC for human PPI prediction is 0.97.
──────────────────────────────────────────────────────────────────────
   12 steps · 43s · saved to papers/CrossPPI/runs/…/HITL_001.json
══════════════════════════════════════════════════════════════════════

you> thanks, what about yeast?
agent> We haven't investigated yeast PPI performance yet — want me to run that now?
```

Type `help` inside the REPL for available commands. `exit` or Ctrl-D to quit.

#### Session memory

`hitl_main` saves a **per-project memory file** at `papers/<slug>/.hitl_memory.json` automatically. It stores two things:

| What | Purpose |
|------|---------|
| **Gateway conversation history** (last 40 messages) | The gateway remembers every question asked and every answer found across sessions — so follow-ups like "what was that number again?" are answered instantly from memory without re-running the pipeline |
| **Repo overview** (from the first triage) | The triage agent's description of the paper and repo is cached so that **on every subsequent question — including in a new session — the paper is not re-read from scratch**. Only a targeted file search for the new question runs instead |

On startup, if a memory file exists, you'll see:
```
memory: 5 previous turn(s) loaded from last session.
```

The memory file lives inside `papers/` which is gitignored, so it stays local to each contributor.

## Benchmark

The evaluated benchmark is in `benchmark_42.csv` at the repo root — 46 questions across 18 repos in the Paper2AgentBench compbio format (`biorxiv_link`, `question`, `ground_truth`, `repo`). These are the questions confirmed to be answerable by the current pipeline (31 from the broader compbio set, 6 PPLM, 5 MetaPoint, 4 CrossPPI).

## Project Structure

```
research_agents/
├── agents/
│   ├── research_agent.py   # Structured single-agent definition
│   ├── react_agent.py      # ReAct worker + improved/plus-plus variants
│   ├── critic_agent.py     # Dependency/integrity critic
│   └── hitl_agents.py      # Triage, setup, execution, read-only HITL agents
├── teams/
│   ├── solo.py             # Single-worker team
│   ├── worker_critic.py    # Worker + critic baseline
│   ├── worker_critic_plus.py        # + improved prompt + setup scripts
│   ├── worker_critic_plus_plus.py   # + plus-plus prompt
│   ├── human_in_the_loop.py         # Three-stage HITL pipeline
│   └── worker_critic_plus_plus_hitl.py  # Plus-plus + Claude operator channel
├── tools/
│   ├── paper_tools.py      # Local paper text extraction tool
│   ├── repo_tools.py       # Read-only repository inspection tools
│   └── exec_tools.py       # File writing, command execution, workspace I/O
├── orchestration.py        # Worker + critic retry loop
├── hitl.py                 # Human channel protocol, integrity guard
├── claude_human.py         # Claude-backed autonomous operator channel
├── project.py              # Local project resolution and venv setup
├── config.py               # API key and model settings
├── main.py                 # Structured-agent CLI entry point
├── react_main.py           # ReAct/Paper2AgentBench CLI entry point
└── hitl_main.py            # Interactive HITL chat REPL
```

## How It Works

The ReAct worker has 15 tools:

**Reading tools** — read the paper, list/find/resolve/search repo files, read repo files.

**Execution tools** — inspect the shared venv, write files to workspace, stage repo files into workspace, run commands from workspace, list/read workspace files, list/stage/cache paper-level artifacts.

Every paper gets one shared isolated Python virtual environment (created automatically via `uv venv --seed`) under `papers/<slug>/.venv`. The `--seed` flag pre-installs `pip`, `setuptools`, and `wheel` so the agent can `pip install` dependencies immediately without affecting the system Python. Each CLI run still gets a fresh `runs/<run-id>/workspace/` for scripts and outputs.

The default team is `solo`. The `worker-critic-plus-plus` team is the strongest fully-automated option: its worker uses a repo-first search strategy, gates execution behind a static-file check, and mandates a second strategy before reporting blocked. The HITL teams add an interactive human (or Claude) operator channel on top of this.

## Known Limitations

- **Fixed local layout**: Each project must contain `paper.pdf` and `repo/` directly under the project folder.
- **Text-only PDF extraction**: Only extracted text is available. Images, figures, and tables rendered as images are not captured.
- **No GPU access**: The agent's venv doesn't have GPU-accelerated packages by default. Large model scripts may fail without manual setup.
