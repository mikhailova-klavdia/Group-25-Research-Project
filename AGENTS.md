# AGENTS.md

Project-level instructions for any coding agent (Claude Code, Codex CLI, Cursor, Gemini CLI, etc.) working in this repo. Quick reference only — narrative detail lives elsewhere.

- **Setup walkthrough, run examples, paper layout**: [README.md](README.md)
- **Architecture deep dive, 6-phase agent workflow, tool tables, benchmark results**: [explanation.md](explanation.md)

Do not duplicate either of the above here; link to them.

## Project at a glance

Single-agent system that reads a research paper + its source repository and reproduces the paper's experiments end-to-end. Built on the OpenAI Agents SDK (`openai-agents`). Returns a structured Pydantic `ResearchAnswer` with one `ExperimentResult` per attempted experiment, plus an `execution_attempted: bool` flag.

## Setup

```bash
uv sync
cp .env.example .env       # put your real OPENAI_API_KEY into .env
```

Python 3.12+ required. Dependencies are pinned in `pyproject.toml`.

## Commands

Run the test suite:

```bash
uv run python -m pytest tests/
```

Two non-obvious parts of that incantation:

- **`python -m`** so the project root is on `sys.path`. The `research_agents` package is not installed; plain `pytest` fails to import it.
- **`tests/`** as an explicit path so collection does not recurse into the cloned-paper repos under `papers/`, which would error out (missing numpy, etc.).

Run the agent on a question:

```bash
uv run python -m research_agents.main --project papers/<slug> --question "..."
```

Optional flags:

- `--trace` — write a local JSONL trace at `papers/<slug>/runs/<run-id>/trace.jsonl` (use this when the OpenAI dashboard is not available; no login required).
- `--model gpt-5-mini-2025-08-07` — stronger reasoning. Default is `gpt-4.1-mini-2025-04-14`.

## Architecture (key files)

- **Agent definition + system prompt**: `research_agents/agents/research_agent.py`
- **9 custom `@function_tool` tools**:
  - Reading: `research_agents/tools/paper_tools.py`, `research_agents/tools/repo_tools.py`
  - Execution: `research_agents/tools/exec_tools.py`
- **Per-run workspace + venv resolution**: `research_agents/project.py`
- **Local trace processor (opt-in)**: `research_agents/tracing.py`
- **CLI entry**: `research_agents/main.py`

Per-run isolation: every invocation creates a fresh `papers/<slug>/runs/<run-id>/.venv/` (via `uv venv --seed`) and `runs/<run-id>/workspace/`. The `repo/` directory is shared across runs and treated as **input-only**. See `explanation.md` for the 6-phase workflow, tool tables, and current benchmark results.

## Code style (match existing patterns)

The codebase has a consistent commenting style. New code must match it.

- **Module-level docstring** at the top of every new file describing its purpose. Model: `research_agents/tools/exec_tools.py:1-14`.
- **"Why" comments on constants** — explain the reasoning behind the number, not the number itself. Model: the `MAX_OUTPUT_BYTES = 50_000` block in `exec_tools.py`.
- **Docstrings with rationale on every function**. Model: `_ensure_venv` in `research_agents/project.py`.
- **Field-level comments on Pydantic models** explaining when/why each field is set. Model: `ExperimentResult` in `research_agents/agents/research_agent.py`.
- **No "what" comments** for obvious code. Default to no comment; add one only when the reasoning is non-obvious.

## Conventions & pitfalls

- **`papers/` is gitignored.** It is per-contributor local workspace (paper PDFs + cloned repos + run outputs). Never commit anything inside.
- **`repo/` is input-only by prompt convention.** The agent prompt forbids writing there; `write_file` sandboxes into `workspace/`. This is **not filesystem-enforced** — a determined `execute_command` could still escape via `cd ..` or `python -c "open('../repo/...', 'w')"`. Treat any apparent write to `repo/` as a bug.
- **Bare `python` / `pip install` inside `execute_command` already routes to the per-run venv** via `PATH` injection. Tools should not hard-code absolute interpreter paths.
- **Tests are pure-function unit tests over tmp dirs.** No live-LLM calls in the suite. When adding a tool, test the pure helper (e.g. `write_file_text`), not the `@function_tool`-decorated wrapper.
- **`OPENAI_API_KEY` lives in `.env`** (gitignored). `.env.example` ships a placeholder only. Never paste a real key into any tracked file, including markdown.

## Adding a new tool

1. Write the function in a file under `research_agents/tools/`.
2. Decorate with `@function_tool`.
3. Take `RunContextWrapper[ResearchContext]` as the first argument — paths are injected here, never exposed to the LLM.
4. Wrap a pure helper (e.g. `write_file_text`) that takes plain strings / paths. Unit-test the helper directly in `tests/`.
5. Register the new tool in the `tools=[...]` list of `create_research_agent()` in `research_agents/agents/research_agent.py`.

## Commit policy

- **Do not commit without explicit user approval.** The user tests changes locally before anything lands in git history.
- **Match the existing commit style.** One short sentence, sentence case, no body, no co-author or tool-attribution tags. Run `git log --oneline -5` for examples.
- **Stage explicit paths** (`git add path/to/file`) rather than `git add .` to avoid accidentally including secrets, large generated artifacts, or unrelated untracked files.
- **Never bypass hooks** (`--no-verify`, `--no-gpg-sign`) unless the user explicitly asks.
