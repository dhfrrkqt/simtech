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

# 에이전트 및 시나리오 관련 모듈들을 임포트합니다.
from curator_agent.scenarios import Branch, Stage, get_scenario
from curator_agent.voice_input import transcribe_audio_bytes
from evaluator_agent.agent_executor import build_message as build_eval_message
from evaluator_agent.agent_executor import build_runtime as build_eval_runtime
from evaluator_agent.scenarios import build_eval_prompt
from dotenv import load_dotenv

# 기본 시간 제한 (초) 설정
DEFAULT_TIME_LIMIT_SECONDS = 240
# UI 파일들이 위치한 디렉토리 경로 설정
UI_DIR = Path(__file__).parent / "UI"

# .env 파일로부터 환경 변수를 로드합니다.
load_dotenv()

@dataclass
class SessionState:
    """사용자 세션의 상태를 저장하는 데이터 클래스입니다."""
    session_id: str          # 세션 고유 ID
    scenario_key: str        # 현재 진행 중인 시나리오 키
    stage_index: int = 0      # 현재 스테이지 인덱스
    affinity: int = 0         # NPC와의 호감도
    trust: int = 0            # NPC와의 신뢰도
    final_rank: str | None = None  # 최종 랭크 (S, A, B, C, F)
    completed: bool = False   # 대화 완료 여부
    recovery_pending: bool = False  # 복구 모드 활성화 여부 (실수 만회 기회 등)
    last_branch: Branch | None = None # 마지막으로 진입한 분기점
    transcript: list[str] = field(default_factory=list) # 대화 내역 전체
    start_time: float = field(default_factory=time.monotonic) # 세션 시작 시간
    time_limit_seconds: int = DEFAULT_TIME_LIMIT_SECONDS # 세션 시간 제한
    api_choice: str = "gemini" # 사용자가 선택한 AI API (gemini 또는 openai)

# 활성화된 모든 세션을 저장하는 딕셔너리
SESSIONS: dict[str, SessionState] = {}

def _get_time_limit(value: Any) -> int:
    """환경 변수 또는 사용자 입력으로부터 시간 제한 값을 가져옵니다."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = int(os.getenv("SCENARIO_TIME_LIMIT_SECONDS", DEFAULT_TIME_LIMIT_SECONDS))
    return max(30, min(limit, 600)) # 최소 30초, 최대 600초로 제한

def _build_stage_payload(stage: Stage, index: int, total: int) -> dict[str, Any]:
    """프론트엔드에 전달할 스테이지 정보를 구성합니다."""
    return {
        "key": stage.key,
        "title": stage.title,
        "prompt": stage.prompt,
        "index": index + 1,
        "total": total,
    }

def _session_timeout(session: SessionState) -> bool:
    """세션이 제한 시간을 초과했는지 확인합니다."""
    return time.monotonic() - session.start_time >= session.time_limit_seconds

async def _run_evaluator(transcript: list[str], api_choice: str = "gemini") -> str:
    """
    대화 기록을 평가하여 피드백 텍스트를 반환합니다.
    api_choice에 따라 Gemini 또는 OpenAI를 사용합니다.
    """
    if api_choice == "openai":
        # OpenAI 사용 (LiteLLM)
        import litellm
        import os
        from dotenv import load_dotenv
        from evaluator_agent.agent import EVALUATOR_PROMPT
        
        load_dotenv()
       openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
        
        # 평가 프롬프트 구성
        eval_prompt_content = build_eval_prompt("standup", transcript)
        
        messages = [
            {"role": "system", "content": EVALUATOR_PROMPT},
            {"role": "user", "content": eval_prompt_content}
        ]
        
        # LiteLLM으로 OpenAI 호출
        response = await litellm.acompletion(
            model="gpt-4",
            messages=messages,
            api_key=openai_key
        )
        
        return response['choices'][0]['message']['content']
    
    else:
        # Gemini 사용 (기존 ADK 로직)
        eval_runner, eval_session = await build_eval_runtime(api_choice="gemini")
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
    """랭크에 따른 점수 문자열을 반환합니다."""
    if final_rank == "S":
        return "5 / 5"
    if final_rank == "B":
        return "3 / 5"
    if final_rank == "F":
        return "1 / 5"
    return "--"

def _score_to_rank(score_25: int) -> str | None:
    """25점 만점 점수를 랭크로 변환합니다."""
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
    """평가 텍스트에서 'Score: X / Y' 형식의 점수를 추출합니다."""
    match = re.search(r"Score:\s*([0-9]+)\s*/\s*([0-9]+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))

class UIRequestHandler(SimpleHTTPRequestHandler):
    """HTTP 요청을 처리하는 핸들러 클래스입니다."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # UI 디렉토리를 루트로 설정하여 정적 파일을 서빙합니다.
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # 로그 출력을 생략합니다 (콘솔을 깨끗하게 유지하기 위해).
        return

    def _json_response(self, payload: dict[str, Any], status: int = 200) -> None:
        """JSON 응답을 클라이언트에 전송합니다."""
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
        """POST 요청의 바디 데이터를 JSON으로 읽어옵니다."""
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:
        """GET 요청 처리 (설정 정보 조회 등)"""
        if self.path == "/api/config":
            self._handle_config()
            return
        if self.path.startswith("/api/"):
            self._json_response({"error": "Not found"}, status=404)
            return
        super().do_GET()

    def do_POST(self) -> None:
        """POST 요청 처리 (시작, 메시지 전송, 음성 데이터 등)"""
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
        """새로운 대화 세션을 시작합니다."""
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
        """사용자의 텍스트 메시지를 처리하고 NPC의 응답을 생성합니다."""
        payload = self._read_body()
        session_id = payload.get("session_id")
        text = str(payload.get("text", "")).strip()
        if not session_id or session_id not in SESSIONS:
            self._json_response({"error": "Invalid session"}, status=400)
            return
        session = SESSIONS[session_id]
        scenario = get_scenario()

        # 이미 종료된 세션인 경우 중복 처리 방지
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

        # 타임아웃 체크
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

        # 복구 로직 처리 (실수한 경우 다시 기회를 주는 등)
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
            # 일반적인 대화 흐름 처리
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

                # 분기에 따른 후속 조치 (복구 제안 혹은 대화 종료)
                if stage.recovery and stage.recovery.should_offer(branch):
                    session.recovery_pending = True
                    coach_prompt = "Sarah looks cold. How do you respond?"
                elif branch.ends_conversation:
                    session.completed = True
                    session.final_rank = "F"
                else:
                    session.stage_index += 1

                # 마지막 스테이지 처리
                if stage.key == "STAGE_4" and not session.recovery_pending:
                    session.final_rank = branch.final_rank or "B"
                    session.completed = True
                    ended_with_stage4_response = True

        if session.completed and not session.recovery_pending and not ended_with_stage4_response:
            if scenario.success_message and scenario.success_message != sarah_response:
                success_message = scenario.success_message

        # 다음 스테이지 정보 준비
        next_stage = None
        if not session.completed and session.stage_index < len(scenario.stages):
            next_stage = _build_stage_payload(
                scenario.stages[session.stage_index],
                session.stage_index,
                len(scenario.stages),
            )

        # 대화가 종료된 경우 평가 에이전트 실행
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
        """음성 데이터를 텍스트로 변환(STT)합니다."""
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
        """UI 설정을 반환합니다."""
        self._json_response(
            {
                "record_seconds_default": int(os.getenv("UI_RECORD_SECONDS", "5")),
            }
        )

def main() -> None:
    """서버 진입점 함수입니다."""
    if not UI_DIR.exists():
        raise SystemExit(f"UI directory not found: {UI_DIR}")
    # 환경 변수에서 포트 번호를 읽어오며, 없으면 8000번을 기본으로 사용합니다.
    port = int(os.getenv("UI_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), UIRequestHandler)
    print(f"UI server running at http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
