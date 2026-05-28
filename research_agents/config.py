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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
MODEL_COSTS = {
    DEFAULT_MODEL: {
        "input_per_million": 0.40,
        "output_per_million": 1.60,
    },
    ALTERNATE_MODEL: {
        "input_per_million": 0.25,
        "output_per_million": 2.00,
    },
}
