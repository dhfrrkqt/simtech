import os

from google.adk.agents import Agent
from google.adk.models import Gemini
from dotenv import load_dotenv


SYSTEM_PROMPT = (
    "You are a friendly cafe staff assistant. "
    "Keep responses concise, warm, and practical. "
    "When confirming an order, repeat the drink, size, and hot/ice choice. "
    "Ask a brief follow-up question when helpful."
)

DEFAULT_MODEL = "gemini-2.0-flash"


def _require_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing GOOGLE_API_KEY environment variable. "
            "Set it before running the agent."
        )
    return api_key


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}

def _env_value(name: str, default: str) -> str:
    raw = os.getenv(name)
    if not raw:
        return default
    return raw.strip()


def build_agent() -> Agent:
    load_dotenv()
    api_key = _require_api_key()
    if not _env_flag("USE_GEMINI", True):
        raise RuntimeError("USE_GEMINI is disabled in .env; no ADK model configured.")

    use_vertex = _env_flag("GOOGLE_GENAI_USE_VERTEXAI", False)
    model_name = _env_value("GEMINI_MODEL", DEFAULT_MODEL)
    model = Gemini(
        model=model_name,
        api_key=api_key,
        use_vertexai=use_vertex,
    )
    return Agent(
        name="curator_daily_chat",
        description="Daily conversation helper.",
        model=model,
        instruction=SYSTEM_PROMPT,
    )
