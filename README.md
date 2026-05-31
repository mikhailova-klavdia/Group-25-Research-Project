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

# Create your .env file with your API key
cp .env.example .env
# Edit .env and add your actual OPENAI_API_KEY

# Install dependencies
uv sync
```

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

## Evaluation Corpus

The agent is tested against a local `papers/<slug>/` workspace per paper. `papers/` is gitignored — contributors clone the repos and download the PDFs locally. Benchmark questions and (where available) ground truths come from [Paper2AgentBench](https://github.com/jmiao24/Paper2AgentBench):

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

The four compbio chains in `question-answers/` can be run with the commands below. `react_main.py` now uses the worker + critic team by default; add `--no-critic` to reproduce the older single-agent ReAct path. With no `--model` flag, runs use the default model `gpt-4.1-mini-2025-04-14`. The worker is allowed up to **150 turns** per attempt, and the critic gets a separate 10-turn review budget.

```bash
uv run python -m research_agents.react_main \
    --project papers/PPLM \
    --questions-file question-answers/PPLM.json

uv run python -m research_agents.react_main \
    --project papers/CrossPPI \
    --questions-file question-answers/CROSSPPI.json

uv run python -m research_agents.react_main \
    --project papers/metapointfinder \
    --questions-file question-answers/METAPOINT.json

uv run python -m research_agents.react_main \
    --project papers/SKiM-GPT \
    --questions-file question-answers/SKIMGPT.json
```

**Full parameter summary for these runs:**

| Parameter | Value |
|-----------|-------|
| Model | `gpt-4.1-mini-2025-04-14` (default — no `--model` flag passed) |
| Max turns | 150 worker turns per attempt, 10 critic turns |
| Questions per repo | 6 / 6 / 5 / 5 (PPLM / CrossPPI / metapointfinder / SKiM-GPT) |
| Isolation | Fresh workspace per question, shared `.venv/` per paper |
| BioRxiv URL | not supplied (`repo_link: ""` in all output files) |

Each question generates one JSON file under `papers/<slug>/runs/<run-id>/<ID>.json` with the full ReAct chain (thought / action / observation / reflection per step), final answer, heuristic `correct` flag, token usage, and any `critic_reviews` / dependency `install_events`.

## Interactive human-in-the-loop CLI

The `human-in-the-loop` team adds a **chat REPL** where the agents ask *you* for help when they're stuck (a token, a workaround, a go/no-go) and stream what they're doing as they work. It's a three-stage crew: a **triage scout** decides whether a question needs code execution; **read-only** questions ("What is this paper about?") are answered straight from the paper/repo text with no environment setup; execution questions go through an interactive **setup engineer** (which prepares the venv with no config file — it discovers deps from the repo and asks you when stuck) and then a worker + integrity critic.

```bash
uv run python -m research_agents.hitl_main --project papers/tabpfn
```

Type a question or task at the `you>` prompt:

- **Read-only** — answers in seconds, no setup: `In one sentence, what is the key idea behind this paper?`
- **Execution** — the agents set up and run; if they hit a wall (e.g. TabPFN's license-gated weights) they ask you, and you suggest a fix inline (e.g. "use the open V2 model"), then they apply it and continue.

REPL commands: `verbose on|off` (full reasoning-chain dump), `help`, `exit`. Defaults to `gpt-5-mini-2025-08-07` (the agents must reliably decide to ask for help); pass `--model gpt-4.1-mini-2025-04-14` for the cheaper one. Each task saves a chain JSON under `papers/<slug>/runs/<run-id>/`.

The same team is selectable headlessly via `react_main --team human-in-the-loop`; with no operator attached, `ask_human` degrades to "proceed autonomously".

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

## Project Structure

```
research_agents/
├── agents/
│   ├── research_agent.py   # Structured single-agent definition
│   ├── react_agent.py      # ReAct worker definition
│   ├── critic_agent.py     # Dependency/integrity critic definition
│   └── hitl_agents.py      # Triage, read-only, setup & execution HITL agents
├── teams/                  # Composable agent teams (selected via --team)
│   ├── solo.py / worker_critic.py / worker_critic_plus.py
│   └── human_in_the_loop.py  # Triage → read-only | setup → execution + integrity guard
├── tools/
│   ├── paper_tools.py      # Local paper text extraction tool
│   ├── repo_tools.py       # Read-only repository inspection tools
│   └── exec_tools.py       # File writing, command execution, workspace I/O
├── orchestration.py        # Worker + critic retry loop
├── hitl.py                 # Human channel + ask_human tool + progress reporter + integrity guard
├── project.py              # Local project resolution and venv setup
├── config.py               # API key and model settings
├── main.py                 # Structured-agent CLI entry point
├── react_main.py           # ReAct/Paper2AgentBench CLI entry point
└── hitl_main.py            # Interactive human-in-the-loop chat CLI
```

## How It Works

The structured agent has nine tools, and the ReAct worker has the same set plus `venv_status()`:

**Reading tools** — read the paper, list repo files, search repo, read repo files.

**Execution tools** — inspect the shared venv, write files to workspace, stage repo files into workspace, run commands from workspace, list workspace files, read workspace files.

Every paper gets one shared isolated Python virtual environment (created automatically via `uv venv --seed`) under `papers/<slug>/.venv`. The `--seed` flag pre-installs `pip`, `setuptools`, and `wheel` so the agent can `pip install` dependencies immediately without affecting the system Python. Each CLI run still gets a fresh `runs/<run-id>/workspace/` for scripts and outputs.

The ReAct CLI defaults to a simple multi-agent team: a worker answers the question, host code captures real tool outputs, a narrow critic reviews dependency/integrity issues, and the worker may retry once with deterministic dependency installs or a critic hint. Use `--no-critic` for the old single-worker behavior.

The `human-in-the-loop` team (run via `hitl_main`, see above) goes further: a triage scout routes read-only questions to a direct paper/repo answer (skipping environment setup entirely), while execution questions get an interactive setup engineer plus the worker + critic — and any agent can pause to ask the operator for help via `ask_human`. A deterministic integrity guard then downgrades any "answered" result that no successful command actually produced.

The agent follows a six-phase workflow: **understand** the paper and question, **plan** which experiments to reproduce, **setup** the workspace with dependencies and staged files, **execute** each experiment, **interpret** outputs and compare with the paper, and **report** structured results with a reproducibility assessment.

## Known Limitations

- **Fixed local layout**: Each project must contain `paper.pdf` and `repo/` directly under the project folder.
- **Text-only PDF extraction**: Only extracted text is available. Images, figures, and tables rendered as images are not captured.
- **No GPU access**: The agent's venv doesn't have GPU-accelerated packages by default. Large model scripts may fail without manual setup.
