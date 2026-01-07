from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from curator_agent.scenarios import Branch, Stage, get_scenario
from curator_agent.voice_input import transcribe_audio_bytes
from evaluator_agent.agent_executor import build_message as build_eval_message
from evaluator_agent.agent_executor import build_runtime as build_eval_runtime
from evaluator_agent.scenarios import build_eval_prompt
from dotenv import load_dotenv


DEFAULT_TIME_LIMIT_SECONDS = 240
UI_DIR = Path(__file__).parent / "UI"

load_dotenv()


@dataclass
class SessionState:
    session_id: str
    scenario_key: str
    stage_index: int = 0
    affinity: int = 0
    trust: int = 0
    final_rank: str | None = None
    completed: bool = False
    recovery_pending: bool = False
    last_branch: Branch | None = None
    transcript: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.monotonic)
    time_limit_seconds: int = DEFAULT_TIME_LIMIT_SECONDS
    api_choice: str = "gemini"


SESSIONS: dict[str, SessionState] = {}


def _get_time_limit(value: Any) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = int(os.getenv("SCENARIO_TIME_LIMIT_SECONDS", DEFAULT_TIME_LIMIT_SECONDS))
    return max(30, min(limit, 600))


def _build_stage_payload(stage: Stage, index: int, total: int) -> dict[str, Any]:
    return {
        "key": stage.key,
        "title": stage.title,
        "prompt": stage.prompt,
        "index": index + 1,
        "total": total,
    }


def _session_timeout(session: SessionState) -> bool:
    return time.monotonic() - session.start_time >= session.time_limit_seconds


async def _run_evaluator(transcript: list[str], api_choice: str = "gemini") -> str:
    eval_runner, eval_session = await build_eval_runtime(api_choice=api_choice)
    eval_prompt = build_eval_prompt("standup", transcript)
    events = eval_runner.run_async(
        user_id=eval_session.user_id,
        session_id=eval_session.id,
        new_message=build_eval_message(eval_prompt),
    )
    chunks: list[str] = []
    async for event in events:
        content = getattr(event, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        if getattr(event, "author", "") == "user":
            continue
        text = "".join(part.text or "" for part in content.parts)
        if text:
            chunks.append(text)
    await eval_runner.close()
    return "".join(chunks)


def _calculate_score(final_rank: str | None) -> str:
    if final_rank == "S":
        return "5 / 5"
    if final_rank == "B":
        return "3 / 5"
    if final_rank == "F":
        return "1 / 5"
    return "--"


def _score_to_rank(score_25: int) -> str | None:
    if score_25 >= 20:
        return "S"
    if score_25 >= 16:
        return "A"
    if score_25 >= 12:
        return "B"
    if score_25 >= 8:
        return "C"
    if score_25 >= 1:
        return "F"
    return None


def _extract_score(text: str) -> tuple[int, int] | None:
    match = re.search(r"Score:\s*([0-9]+)\s*/\s*([0-9]+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


class UIRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json_response(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:
        if self.path == "/api/config":
            self._handle_config()
            return
        if self.path.startswith("/api/"):
            self._json_response({"error": "Not found"}, status=404)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/start":
            self._handle_start()
            return
        if self.path == "/api/message":
            self._handle_message()
            return
        if self.path == "/api/voice":
            self._handle_voice()
            return
        self._json_response({"error": "Not found"}, status=404)

    def _handle_start(self) -> None:
        payload = self._read_body()
        scenario = get_scenario()
        session_id = uuid.uuid4().hex
        time_limit = _get_time_limit(payload.get("timeout_seconds"))
        session = SessionState(
            session_id=session_id,
            scenario_key=scenario.key,
            time_limit_seconds=time_limit,
            api_choice=payload.get("api_choice", "gemini"),
        )
        SESSIONS[session_id] = session
        stage = scenario.stages[0]
        self._json_response(
            {
                "session_id": session_id,
                "scenario": {
                    "title": scenario.title,
                    "background": scenario.background,
                    "npc_state": scenario.npc_state,
                    "items": scenario.items,
                },
                "stage": _build_stage_payload(stage, 0, len(scenario.stages)),
                "record_seconds_default": int(os.getenv("UI_RECORD_SECONDS", "5")),
            }
        )

    def _handle_message(self) -> None:
        payload = self._read_body()
        session_id = payload.get("session_id")
        text = str(payload.get("text", "")).strip()
        if not session_id or session_id not in SESSIONS:
            self._json_response({"error": "Invalid session"}, status=400)
            return
        session = SESSIONS[session_id]
        scenario = get_scenario()

        if session.completed:
            self._json_response(
                {
                    "completed": True,
                    "final_rank": session.final_rank,
                    "score": _calculate_score(session.final_rank),
                    "system": "The session has already ended.",
                }
            )
            return

        if _session_timeout(session):
            session.completed = True
            session.final_rank = session.final_rank or "F"
            self._json_response(
                {
                    "completed": True,
                    "sarah": scenario.fail_message,
                    "system": "Sarah leaves her seat to head to the next meeting.",
                    "final_rank": session.final_rank,
                    "score": _calculate_score(session.final_rank),
                }
            )
            return

        if not text:
            self._json_response({"error": "Empty input"}, status=400)
            return

        session.transcript.append(f"You: {text}")

        sarah_response = None
        coach_prompt = None
        success_message = None
        ended_with_stage4_response = False

        if session.recovery_pending and session.stage_index < len(scenario.stages):
            stage = scenario.stages[session.stage_index]
            recovery = stage.recovery.match(text) if stage.recovery else None
            if recovery:
                session.affinity += recovery.affinity_delta
                session.trust += recovery.trust_delta
                sarah_response = recovery.response
                session.transcript.append(f"Sarah: {sarah_response}")
                session.recovery_pending = False
                session.stage_index += 1
            else:
                if session.last_branch and session.last_branch.ends_conversation:
                    session.completed = True
                    session.final_rank = "F"
                    sarah_response = "The conversation has ended."
                else:
                    sarah_response = "Understood."
                    session.recovery_pending = False
                    session.stage_index += 1
        else:
            if session.stage_index >= len(scenario.stages):
                session.completed = True
            else:
                stage = scenario.stages[session.stage_index]
                branch = stage.match(text)
                session.last_branch = branch
                session.affinity += branch.affinity_delta
                session.trust += branch.trust_delta
                sarah_response = branch.response
                session.transcript.append(f"Sarah: {sarah_response}")

                if stage.recovery and stage.recovery.should_offer(branch):
                    session.recovery_pending = True
                    coach_prompt = "Sarah looks cold. How do you respond?"
                elif branch.ends_conversation:
                    session.completed = True
                    session.final_rank = "F"
                else:
                    session.stage_index += 1

                if stage.key == "STAGE_4" and not session.recovery_pending:
                    session.final_rank = branch.final_rank or "B"
                    session.completed = True
                    ended_with_stage4_response = True

        if session.completed and not session.recovery_pending and not ended_with_stage4_response:
            if scenario.success_message and scenario.success_message != sarah_response:
                success_message = scenario.success_message

        next_stage = None
        if not session.completed and session.stage_index < len(scenario.stages):
            next_stage = _build_stage_payload(
                scenario.stages[session.stage_index],
                session.stage_index,
                len(scenario.stages),
            )

        eval_text = None
        if session.completed:
            try:
                eval_text = asyncio.run(_run_evaluator(session.transcript, api_choice=session.api_choice))
            except Exception:
                eval_text = None
            if eval_text:
                score_data = _extract_score(eval_text)
                score_25 = None
                if score_data:
                    score_value, score_max = score_data
                    if score_max == 25:
                        score_25 = score_value
                    elif score_max == 5:
                        score_25 = score_value * 5
                rank_from_score = (
                    _score_to_rank(score_25) if score_25 is not None else None
                )
                if rank_from_score:
                    session.final_rank = rank_from_score
            if session.final_rank is None:
                session.final_rank = "B"

        self._json_response(
            {
                "sarah": sarah_response,
                "coach_prompt": coach_prompt,
                "success_message": success_message,
                "completed": session.completed,
                "final_rank": session.final_rank,
                "score": _calculate_score(session.final_rank),
                "evaluation": eval_text,
                "stage": next_stage,
            }
        )

    def _handle_voice(self) -> None:
        payload = self._read_body()
        audio_b64 = payload.get("audio_base64")
        if not audio_b64:
            self._json_response({"error": "Missing audio"}, status=400)
            return
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except (ValueError, TypeError):
            self._json_response({"error": "Invalid audio encoding"}, status=400)
            return

        sample_rate = payload.get("sample_rate", 16000)
        language_code = payload.get("language_code", "en-US")
        try:
            transcript = transcribe_audio_bytes(
                audio_bytes=audio_bytes,
                sample_rate=int(sample_rate),
                language_code=str(language_code),
            )
        except Exception as exc:
            self._json_response({"error": f"STT failed: {exc}"}, status=500)
            return

        self._json_response({"transcript": transcript})

    def _handle_config(self) -> None:
        self._json_response(
            {
                "record_seconds_default": int(os.getenv("UI_RECORD_SECONDS", "5")),
            }
        )


def main() -> None:
    if not UI_DIR.exists():
        raise SystemExit(f"UI directory not found: {UI_DIR}")
    port = int(os.getenv("UI_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), UIRequestHandler)
    print(f"UI server running at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
