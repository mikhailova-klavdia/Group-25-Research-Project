# Loads settings from .env and exposes them as module-level constants.
#
# `load_dotenv()` populates os.environ from a `.env` file in the project
# root.  If the variable is already in the environment (e.g. exported in
# the shell or injected by a CI runner), dotenv does NOT overwrite it, so
# the file is strictly a convenience fallback for local development.

import os

from dotenv import load_dotenv

load_dotenv()

# Validated in main.py before the agent runs; left as None here so importing
# this module for tests / tooling doesn't crash when no key is present.
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")

# The two models we have access to with our key.  Both use the same tool-
# calling interface — the only difference to the agent is cost and capability.
#
# Default: cheaper and faster; suitable for development iteration, simple
# questions, and most single-experiment reproductions.
DEFAULT_MODEL = "gpt-4.1-mini-2025-04-14"
# Alternate: stronger reasoning; picked via `--model` for papers with
# involved multi-step plans, long repos, or ambiguous instructions.
ALTERNATE_MODEL = "gpt-5-mini-2025-08-07"

# Pricing per 1M tokens
MODEL_COSTS: dict[str, dict] = {
    DEFAULT_MODEL: {
        "input_per_million": 0.40,
        "output_per_million": 1.60,
    },
    ALTERNATE_MODEL: {
        "input_per_million": 0.25,
        "output_per_million": 2.00,
    },
}

# Default per-agent turn cap (Runner.run_sync max_turns).  150 is deliberately
# generous so a multi-step reproduction never dies mid-plan.  Batch eval runs
# tighten this via react_main's --max-turns flag to bound a stuck question's
# token burn.
DEFAULT_MAX_TURNS = 150


def resolve_max_turns(default: int = DEFAULT_MAX_TURNS) -> int:
    """Return the per-agent turn cap, honoring a ``RESEARCH_MAX_TURNS`` override.

    react_main's ``--max-turns`` flag exports ``RESEARCH_MAX_TURNS`` so the cap
    crosses the fixed ``team.run(...)`` boundary (which has no max_turns
    parameter) into every agent stage.  Read at call time — not import time —
    so a value set in ``main()`` is visible to the teams in the same process.
    A missing, non-integer, or non-positive value falls back to ``default``,
    preserving the previous behavior for callers that don't opt in.
    """
    raw = os.environ.get("RESEARCH_MAX_TURNS")
    if raw:
        try:
            value = int(raw)
        except ValueError:
            return default
        if value > 0:
            return value
    return default

