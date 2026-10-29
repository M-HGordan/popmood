"""Step 1 | Central configuration: loads .env and exposes API keys, model list, feature toggles and data paths."""
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
if not ENV_PATH.exists():
    print("⚠️ فایل .env پیدا نشد:", ENV_PATH)
load_dotenv(ENV_PATH, encoding="utf-8-sig")


def _env(*names):
    """Return the first non-empty environment variable among *names* (supports legacy aliases), else None."""
    for n in names:
        v = os.getenv(n)
        if v:
            return v.strip()
    return None


# Cloud LLM (gapgpt): models are tried in order
API_KEY = _env("GAPGPT_API_KEY", "API_KEY")
BASE_URL = _env("GAPGPT_BASE_URL", "BASE_URL")
MODELS = [m.strip() for m in (_env("GAPGPT_MODEL", "MODEL") or "").split(",") if m.strip()]

# Behaviour toggles
STREAM = (_env("GAPGPT_STREAM", "STREAM") or "0").lower() in ("1", "true", "yes")

USE_TMDB = (_env("USE_TMDB") or "0").lower() in ("1", "true", "yes")
RACE = (_env("GAPGPT_RACE", "RACE") or "1").lower() in ("1", "true", "yes")

# Optional local fallback model (Ollama)
OLLAMA_MODEL = _env("OLLAMA_MODEL")
OLLAMA_URL = _env("OLLAMA_URL") or "http://localhost:11434/v1"

# Data paths
MOVIES_PATH = "data/movies_sample.json"
TMDB_PATH = "data/movies_tmdb.json"
TMDB_CSV = "data/tmdb_5000_movies.csv"
