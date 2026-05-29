# Joao Victor - 2026-05-28 - gpt-5-mini multi-agent run

This folder contains a full 22-question Paper2AgentBench compbio sweep run by
Joao Victor on 2026-05-28.

This is a benchmark run artifact, not a human-annotation folder.

## Run setup

- Model: `gpt-5-mini-2025-08-07`
- Architecture: ReAct worker plus dependency/integrity critic
- CLI: `research_agents.react_main`
- Fresh generated state before run: old `runs/`, `.venv/`, `.artifacts/`, and `costs.json` were removed for the four target papers.
- PPLM environment: recreated from `papers/PPLM/.research_config.toml` with Python 3.9 and `torch==1.13.1`.

## Commands

```bash
uv run python -m research_agents.react_main --project papers/PPLM --questions-file question-answers/PPLM.json --model gpt-5-mini-2025-08-07
uv run python -m research_agents.react_main --project papers/CrossPPI --questions-file question-answers/CROSSPPI.json --model gpt-5-mini-2025-08-07
uv run python -m research_agents.react_main --project papers/metapointfinder --questions-file question-answers/METAPOINT.json --model gpt-5-mini-2025-08-07
uv run python -m research_agents.react_main --project papers/SKiM-GPT --questions-file question-answers/SKIMGPT.json --model gpt-5-mini-2025-08-07
```

## Contents

- `chains/`: the 22 final chain JSONs copied from `papers/<slug>/runs/<run-id>/<ID>.json`.
- `logs/`: stdout/stderr logs captured while running each paper batch.
- `summary.md`: score and per-question status summary.

The `eval_runs/` copy was populated after the batches completed so these files were not available to the agent while it was answering.
