# Research Agents

Research agents powered by the OpenAI Agents SDK for analyzing scientific papers.

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

## Usage

```bash
uv run python -m research_agents.main \
  --paper "https://www.biorxiv.org/content/10.1101/2025.11.13.688364v1" \
  --question "What does SEGMA stand for, and what therapeutic problem does it address?"
```

To use a different model:

```bash
uv run python -m research_agents.main \
  --paper "https://www.biorxiv.org/content/10.1101/2025.11.13.688364v1" \
  --question "What does SEGMA stand for?" \
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
│   └── paper_tools.py      # Paper download and text extraction tool
├── config.py                # API key and model settings
└── main.py                  # CLI entry point
```

## Known Limitations

- **Biorxiv Cloudflare blocking**: Biorxiv PDFs are often blocked by Cloudflare. The tool falls back to the biorxiv API, which returns only the abstract and metadata (not the full paper text).
- **Text-only PDF extraction**: When PDFs are accessible, only text is extracted. Images, figures, and tables rendered as images are not captured.
- **Analysis only**: The agent reads and analyzes papers but does not execute code from repositories.
