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
  paper.pdf
  repo/
```

- `paper.pdf` is the local paper file.
- `repo/` is the full checked-out repository associated with that paper.
- `papers/` is a local workspace and is ignored by git.

## Usage

```bash
uv run python -m research_agents.main \
  --project papers/segma \
  --question "Which file defines the main model pipeline?"
```

To use a different model:

```bash
uv run python -m research_agents.main \
  --project papers/segma \
  --question "Which file defines the main model pipeline?" \
  --model gpt-5-mini-2025-08-07
```

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
│   └── repo_tools.py       # Read-only repository inspection tools
├── project.py              # Local project resolution
├── config.py                # API key and model settings
└── main.py                  # CLI entry point
```

## Known Limitations

- **Fixed local layout**: Each project must contain `paper.pdf` and `repo/` directly under the project folder.
- **Text-only PDF extraction**: Only extracted text is available. Images, figures, and tables rendered as images are not captured.
- **Read-only repository analysis**: The agent inspects the repository but does not install dependencies or execute repo code.
