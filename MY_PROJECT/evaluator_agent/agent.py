import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models import Gemini


EVALUATOR_PROMPT = (
    "You are a conversation evaluator. "
    "Follow the scenario-specific rubric and respond in Korean. "
    "Evaluate politeness, clarity, and intent alignment. "
    "Give higher scores when honorifics/polite speech are used consistently. "
    "Penalize casual speech. "
    "Return a brief evaluation and a score when requested."
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
    load_dotenv()
    
    if api_choice == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
        # OpenAI용 모델 할당 (ADK에서 OpenAI를 지원하지 않는 경우를 대비해 placeholder 로직 구성 가능)
        # 현재는 유저 요청에 따라 구조를 마련함
        from google.adk.models import Gemini # 우선 Gemini 클래스를 재활용하거나 LiteLLM 등으로 확장 가능
        model = Gemini(model="gpt-4", api_key=api_key) 
    else:
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
