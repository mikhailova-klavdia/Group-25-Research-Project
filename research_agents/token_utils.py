# Utilities for token estimation and cost calculation.
#
# Two functions are provided:
#   estimate_tokens  — counts tokens locally via tiktoken BEFORE a run
#   calculate_cost   — computes dollar cost from real usage AFTER a run
#
# The pre-run estimate is intentionally rough: it only counts the system
# prompt and user question, not tool schemas or SDK overhead. Use it as
# a lower-bound sanity check, not a billing prediction.

import tiktoken

from research_agents.config import MODEL_COSTS, DEFAULT_MODEL
import json
from pathlib import Path
from datetime import datetime, UTC


def estimate_tokens(system_prompt: str, question: str, model: str = DEFAULT_MODEL) -> int:
    """Estimate token count for a run before it starts.

    Uses tiktoken with o200k_base encoding, which covers the gpt-4.1 and
    gpt-5 model families.  Falls back to cl100k_base if the model isn't
    recognised — the difference is small for plain English text.

    This is a lower bound: tool schemas, SDK message wrappers, and
    multi-turn context accumulation all add tokens that tiktoken can't
    see before the run starts.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("o200k_base")

    return len(enc.encode(system_prompt)) + len(enc.encode(question))


def calculate_cost(input_tokens: int, output_tokens: int, model: str = DEFAULT_MODEL) -> float:
    """Calculate estimated cost in USD from real post-run token counts."""
    prices = MODEL_COSTS.get(model, MODEL_COSTS[DEFAULT_MODEL])
    input_cost  = (input_tokens  / 1_000_000) * prices["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * prices["output_per_million"]
    return input_cost + output_cost

def load_cost_log(project_dir: Path) -> list:
    """Load existing cost log entries from the project folder."""
    log_path = project_dir / "costs.json"
    if not log_path.exists():
        return []
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def append_cost_log(
    project_dir: Path,
    run_id: str,
    question: str,
    model: str,
    pre_estimate: int,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Append one run's usage to costs.json in the project folder."""
    log_path = project_dir / "costs.json"
    entries = load_cost_log(project_dir)

    cost = calculate_cost(input_tokens, output_tokens, model)
    entries.append({
        "timestamp":   datetime.now(UTC).isoformat(),
        "run_id":      run_id,
        "model":       model,
        "question":    question[:120],   # truncate so the file stays readable
        "pre_estimate_tokens": pre_estimate,
        "input_tokens":        input_tokens,
        "output_tokens":       output_tokens,
        "total_tokens":        input_tokens + output_tokens,
        "cost_usd":            round(cost, 6),
    })

    log_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def print_token_report(
    pre_estimate: int,
    input_tokens: int,
    output_tokens: int,
    model: str = DEFAULT_MODEL,
    project_dir: Path | None = None,   # add this parameter
) -> None:
    """Print a tidy token and cost summary, with accumulated totals if available."""
    total = input_tokens + output_tokens
    cost  = calculate_cost(input_tokens, output_tokens, model)

    print(f"\n{'─' * 40}")
    print(f"Token usage — this run")
    print(f"  Pre-run estimate (tiktoken): ~{pre_estimate:,} tokens")
    print(f"  Actual input tokens:          {input_tokens:,}")
    print(f"  Actual output tokens:         {output_tokens:,}")
    print(f"  Actual total tokens:          {total:,}")
    print(f"  Estimated cost:              ${cost:.4f}")

    # Accumulated totals across all runs for this paper project
    if project_dir is not None:
        entries = load_cost_log(project_dir)
        if entries:
            total_tokens_all = sum(e["total_tokens"] for e in entries)
            total_cost_all   = sum(e["cost_usd"]     for e in entries)
            print(f"\nAccumulated ({len(entries)} runs on this project)")
            print(f"  Total tokens spent:  {total_tokens_all:,}")
            print(f"  Total cost:         ${total_cost_all:.4f}")

    print(f"{'─' * 40}")