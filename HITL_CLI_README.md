# Interactive Agent CLI — User Guide

The interactive CLI (`hitl_main.py`) lets you talk to any registered agent team from a chat prompt, step through benchmark question files one-by-one, or run triage-only previews before committing to a full run. It replaces copy-pasting commands into `react_main` for exploratory or semi-supervised work.

---

## Quick start

```bash
# 1. Make sure your API key is set
cp .env.example .env    # then add your OPENAI_API_KEY

# 2. Install dependencies
uv sync

# 3. Start the REPL for any paper project
uv run python -m research_agents.hitl_main --project papers/PPLM
```

You will see:

```
══════════════════════════════════════════════════════════════════════
Research Agent — interactive CLI
  project : papers/PPLM
  team    : human-in-the-loop  —  Two-stage human-in-the-loop crew…
  model   : gpt-5-mini-2025-08-07
  Ask a question or give a task. Type 'help' for commands, 'exit' to quit.
══════════════════════════════════════════════════════════════════════

you>
```

Type any question. Press Enter. The agent streams what it is doing. If it needs your help (a missing credential, a workaround), it pauses and asks you directly.

---

## All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--project PATH` | *(required)* | Path to a folder containing `paper.pdf` and `repo/` |
| `--team NAME` | `human-in-the-loop` | Agent team to use (see [Teams](#teams)) |
| `--model NAME` | `gpt-5-mini-2025-08-07` | Model to use (see [Models](#models)) |
| `--questions-file PATH` | *(off)* | JSON questions file — enables batch mode |
| `--dry-run` | *(off)* | Triage only — shows routing decision without executing |
| `--verbose` | *(off)* | Print full reasoning chain (toggle with `verbose on/off` in REPL) |

---

## Teams

Select with `--team <name>`. All teams work in both the REPL and batch mode.

| Name | What it does | Best for |
|------|-------------|----------|
| `human-in-the-loop` | Triage → read-only answer OR setup engineer → worker + integrity critic. Can ask you for help mid-run. | Exploratory work, stuck questions, new repos |
| `worker-critic-plus` | Improved ReAct worker + critic. Pre-downloads weights from `.research_config.toml`. | Benchmark runs on known papers |
| `worker-critic` | ReAct worker + critic, no pre-setup. | Quick runs, papers without large weights |
| `solo` | Single ReAct worker, no critic. Fastest, least reliable. | Cheap/fast exploration |

```bash
# Use the faster worker-critic-plus for a question you know needs execution
uv run python -m research_agents.hitl_main \
  --project papers/PPLM \
  --team worker-critic-plus

# Use solo for a quick factual read-only check
uv run python -m research_agents.hitl_main \
  --project papers/metapointfinder \
  --team solo \
  --model gpt-4.1-mini-2025-04-14
```

---

## Models

| Name | Cost | Use when |
|------|------|----------|
| `gpt-5-mini-2025-08-07` | Higher | Default for HITL — agents must reliably decide to ask for help |
| `gpt-4.1-mini-2025-04-14` | Lower | Simple questions, large batch runs where cost matters |

```bash
uv run python -m research_agents.hitl_main \
  --project papers/CrossPPI \
  --model gpt-4.1-mini-2025-04-14
```

---

## REPL commands

Type these at the `you>` prompt:

| Command | What it does |
|---------|-------------|
| `<any question>` | Run the agent on that question |
| `history` | Show all questions answered this session with time and cost |
| `verbose on` | Print the full T/A/O/R reasoning chain for every task |
| `verbose off` | Switch back to the clean result-only output |
| `help` | Show available commands and team names |
| `exit` or `quit` | Leave (Ctrl-D also works) |

---

## Example questions to try

### Read-only (instant, no code)

These are answered in seconds from the paper and repo text. No venv setup.

```
you> What is the main contribution of this paper in one sentence?
you> What Python version does this repo require?
you> List all the command-line tools this repo provides and what each one does.
you> What datasets does this paper use and where are they downloaded from?
you> What is the maximum number of training epochs in configs/config.json?
```

### Execution questions

These run actual code. The agent sets up the venv, stages files, and executes scripts.

```
you> Run the PPLM tool with seq1.fasta and seq2.fasta and tell me the shape of the embed_A embeddings.
you> What is the predicted pKD for the RAS-RAF protein pair? Use the pre-trained models in the save/ directory.
you> Run the preprocessing pipeline and tell me how many cells pass QC.
you> Generate mutant protein sequences from the AMR data and count how many total sequences are in the output FASTA.
you> What does running the default example in the README produce?
```

### Asking for help (human-in-the-loop team only)

The agent will pause and ask you when it hits something it cannot resolve alone:

```
you> Run the TabPFN classifier on the example dataset.
```
The agent discovers that the default TabPFN V1 weights are license-gated and asks:
```
┌─ I need a hand ─────────────────────────────────────────────────
│ The default TabPFN checkpoint requires a license agreement.
│ Options: (a) use the open V2 model, (b) provide a token
└────────────────────────────────────────────────────────────────
➜ your answer: use the open V2 model
```
The agent applies your answer and continues.

---

## Batch mode — questions file

Point at any JSON questions file to step through questions one-by-one:

```bash
uv run python -m research_agents.hitl_main \
  --project papers/PPLM \
  --questions-file question-answers/PPLM.json
```

For each question you see:

```
[1/6]  PPLM_001
  Q: Using the PPLM binding affinity prediction tool, predict the binding affinity…
  GT: -8.226562
  Run? [Enter=yes / s=skip / q=quit] >
```

- Press **Enter** or type **y** to run it
- Type **s** to skip and move to the next
- Type **q** to quit the batch loop

After each answered question, the accuracy score updates:

```
  ✅  Matches ground truth
  Running score: 3/4 (75%)
```

A session summary prints when the batch finishes.

### Skip questions you know are blocked

```
[1/6]  PPLM_001   (needs affinity_models.pkl — Google Drive rate-limited)
  Run? [Enter=yes / s=skip / q=quit] > s
  Skipped.

[2/6]  PPLM_002   (same blocker)
  Run? [Enter=yes / s=skip / q=quit] > s
  Skipped.

[3/6]  PPLM_003   ← this one should work
  Run? [Enter=yes / s=skip / q=quit] >
```

### Use with the new question sets

```bash
# GENECAD
uv run python -m research_agents.hitl_main \
  --project papers/GENECAD \
  --questions-file question-answers/GENECAD.json \
  --team worker-critic-plus

# IDEA_DNA_METHYLATION
uv run python -m research_agents.hitl_main \
  --project papers/IDEA_DNA_METHYLATION \
  --questions-file question-answers/IDEA_DNA_METHYLATION.json

# ARCADIA_PUBLIC — mix of read-only and execution
uv run python -m research_agents.hitl_main \
  --project papers/ARCADIA_PUBLIC \
  --questions-file question-answers/ARCADIA_PUBLIC.json
```

---

## Dry-run mode

Preview routing decisions without spending tokens on execution.

### Dry-run a single question in the REPL

```bash
uv run python -m research_agents.hitl_main \
  --project papers/ARCADIA_PUBLIC \
  --dry-run
```

```
you> According to the config file, what is the maximum number of training epochs?

▸ Running triage (dry-run — no execution will happen)…
──────────────────────────────────────────────────────────────────────
  Routing: READ-ONLY (no code needed)
  Rationale: The answer is a static value in a config file, no script execution required.
  Relevant paths: ARCADIA_public/configs/config.json
──────────────────────────────────────────────────────────────────────
```

```
you> Run the preprocessing pipeline and tell me how many cells pass QC.

▸ Running triage (dry-run — no execution will happen)…
──────────────────────────────────────────────────────────────────────
  Routing: EXECUTION REQUIRED
  Rationale: Requires running the preprocessing pipeline to obtain QC statistics.
  Relevant paths: ARCADIA_public/tools/preprocess_cite_seq.py, configs/config.json
──────────────────────────────────────────────────────────────────────
```

### Dry-run an entire questions file

```bash
uv run python -m research_agents.hitl_main \
  --project papers/ARCADIA_PUBLIC \
  --questions-file question-answers/ARCADIA_PUBLIC.json \
  --dry-run
```

Shows routing decisions for all questions so you can plan which ones to skip before running the real batch.

---

## History command

After running several tasks, type `history` to see everything answered this session:

```
you> history
──────────────────────────────────────────────────────────────────────
   1. [HITL_001] ✓  What is the main contribution of this paper?
       → PPLM uses protein language models to predict protein-protein…
       4s  $0.0012
   2. [HITL_002] ✓  Run the PPLM tool with seq1.fasta and tell me…
       → (122, 1280)
       184s  $0.0731
   3. [HITL_003] ⚠  Run binding affinity prediction on receptor.fasta…
       → EXECUTION_REQUIRED — affinity_models.pkl not found after…
       67s  $0.0298
──────────────────────────────────────────────────────────────────────
  Session total cost: $0.1041
──────────────────────────────────────────────────────────────────────
```

A full session summary also prints automatically when you type `exit`.

---

## Output files

Every task saves a JSON chain to:

```
papers/<slug>/runs/<run-id>/<entry-id>.json
```

The JSON contains the full T/A/O/R chain, final answer, critic reviews, token usage, and cost. The same format as `react_main` output, so the same grading scripts and annotation tools work on it.

---

## Troubleshooting

**`OPENAI_API_KEY not set`** — create `.env` with your key or `export OPENAI_API_KEY=sk-...`

**`Missing paper.pdf`** — download the paper PDF and place it at `papers/<slug>/paper.pdf`

**`Missing repo/`** — clone the repo: `git clone <url> papers/<slug>/repo`

**Agent hit the 150-turn limit** — the task was too complex. Try breaking it into smaller sub-questions, or switch to `--team worker-critic-plus` which has a stronger prompt for finding files efficiently.

**Task cost seems high** — switch to `--model gpt-4.1-mini-2025-04-14` for cheaper runs. Use `--dry-run` first to check if a question even needs execution before spending tokens.

**Julia questions (ChainStorm.jl)** — the agent cannot currently execute Julia code. It will read the repo and attempt to answer from code inspection or compute the answer analytically. Execution-dependent questions will be blocked.
