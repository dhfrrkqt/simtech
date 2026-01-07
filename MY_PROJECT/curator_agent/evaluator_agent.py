import os

from google.adk.agents import Agent
from google.adk.models import Gemini
from dotenv import load_dotenv


EVALUATOR_PROMPT = (
    "You are a cafe conversation evaluator. "
    "Evaluate the conversation for politeness, clarity, and order accuracy. "
    "Return a short evaluation and a score from 1 to 5."
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


def build_evaluator_agent() -> Agent:
    load_dotenv()
    api_key = _require_api_key()
    use_vertex = _env_flag("GOOGLE_GENAI_USE_VERTEXAI", False)
    model_name = _env_value("GEMINI_MODEL", DEFAULT_MODEL)
    model = Gemini(
        model=model_name,
        api_key=api_key,
        use_vertexai=use_vertex,
    )
    return Agent(
        name="evaluator_agent",
        description="Cafe conversation evaluator.",
        model=model,
        instruction=EVALUATOR_PROMPT,
    )
