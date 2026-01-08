import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models import Gemini


EVALUATOR_PROMPT = (
    "You are a conversation evaluator. "
    "Follow the scenario-specific rubric and respond in English. "
    "Focus your evaluation on the specific stages or moments that most influenced the final score. "
    "Do not list every stage if it was uneventful; instead, highlight key strengths or weaknesses in areas like icebreakers, clarity, politeness, and intent alignment. "
    "Provide a concise, insightful feedback paragraph followed by the final score in the format 'Score:X/5'."
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


def build_agent(api_choice: str = "gemini") -> Agent:
    """
    Gemini 기반 평가 에이전트를 빌드합니다.
    api_choice 파라미터는 호환성을 위해 유지하지만, Gemini만 사용합니다.
    OpenAI는 ui_server.py의 _run_evaluator에서 LiteLLM으로 직접 호출됩니다.
    """
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
        description="Evaluates cafe ordering conversations.",
        model=model,
        instruction=EVALUATOR_PROMPT,
    )
