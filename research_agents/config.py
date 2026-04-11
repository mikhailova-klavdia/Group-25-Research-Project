# Loads settings from .env and exposes them as module-level constants.

import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# The two models we have access to with our key.
DEFAULT_MODEL = "gpt-4.1-mini-2025-04-14"
ALTERNATE_MODEL = "gpt-5-mini-2025-08-07"
