import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_MODEL = "gpt-4.1-mini-2025-04-14"
ALTERNATE_MODEL = "gpt-5-mini-2025-08-07"
