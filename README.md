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
  runs/
    <run-id>/
      workspace/   # auto-created fresh workspace for this run
      .venv/       # auto-created isolated Python environment for this run
```

- `paper.pdf` is the local paper file.
- `repo/` is the full checked-out repository associated with that paper.
- `runs/<run-id>/workspace/` is auto-created on every CLI run. Agent-generated scripts and outputs live there.
- `runs/<run-id>/.venv/` is a fresh isolated Python environment created for that run only.
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

The four compbio chains in `question-answers/` were produced with the commands below. All runs used **batch mode** (`--questions-file`) with **no `--model` flag**, so every chain was generated by the default model `gpt-4.1-mini-2025-04-14`. The agent was allowed up to **150 turns** (hardcoded in `react_main.py`). No `--biorxiv-url` was supplied, so `repo_link` is `""` in all 22 output JSON files.

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
| Max turns | 150 |
| Questions per repo | 6 / 6 / 5 / 5 (PPLM / CrossPPI / metapointfinder / SKiM-GPT) |
| Isolation | Fresh workspace + venv per question (`resolve_project()` called inside the loop) |
| BioRxiv URL | not supplied (`repo_link: ""` in all output files) |

Each question generates one JSON file under `papers/<slug>/runs/<run-id>/<ID>.json` with the full ReAct chain (thought / action / observation / reflection per step), final answer, and a heuristic `correct` flag.

## Available Models

| Model | Description |
|-------|-------------|
| `gpt-4.1-mini-2025-04-14` | Default. Faster and cheaper for development. |
| `gpt-5-mini-2025-08-07` | More capable. Use for complex analysis. |

## Project Structure

```
research_agents/
├── agents/
│   └── research_agent.py   # Agent definition and instructions
├── tools/
│   ├── paper_tools.py      # Local paper text extraction tool
│   ├── repo_tools.py       # Read-only repository inspection tools
│   └── exec_tools.py       # File writing, command execution, workspace I/O
├── project.py              # Local project resolution and venv setup
├── config.py               # API key and model settings
└── main.py                 # CLI entry point
```

## How It Works

The agent has nine tools organized in two groups:

**Reading tools** — read the paper, list repo files, search repo, read repo files.

**Execution tools** — write files to workspace, stage repo files into workspace, run commands from workspace, list workspace files, read workspace files.

Every CLI run gets a fresh isolated Python virtual environment (created automatically via `uv venv --seed`) under `runs/<run-id>/.venv`. The `--seed` flag pre-installs `pip`, `setuptools`, and `wheel` so the agent can `pip install` dependencies immediately without affecting the system Python or other runs.

The agent follows a six-phase workflow: **understand** the paper and question, **plan** which experiments to reproduce, **setup** the workspace with dependencies and staged files, **execute** each experiment, **interpret** outputs and compare with the paper, and **report** structured results with a reproducibility assessment.

## Known Limitations

- **Fixed local layout**: Each project must contain `paper.pdf` and `repo/` directly under the project folder.
- **Text-only PDF extraction**: Only extracted text is available. Images, figures, and tables rendered as images are not captured.
- **No GPU access**: The agent's venv doesn't have GPU-accelerated packages by default. Large model scripts may fail without manual setup.
