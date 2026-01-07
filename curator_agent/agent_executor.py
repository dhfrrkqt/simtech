from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from curator_agent.agent import build_agent


async def build_runtime() -> tuple[Runner, object]:
    agent = build_agent()
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=agent.name, user_id="local_user"
    )
    return runner, session


def build_message(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])
