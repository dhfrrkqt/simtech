from __future__ import annotations

import asyncio
import os
import re
import select
import sys
import time

from curator_agent.scenarios import get_scenario
from curator_agent.voice_input import VoiceInputError, capture_and_transcribe
from evaluator_agent.agent_executor import build_message as build_eval_message
from evaluator_agent.agent_executor import build_runtime as build_eval_runtime
from evaluator_agent.scenarios import build_eval_prompt

# 종료를 위한 특수 명령어들
EXIT_TOKENS = {"exit", "quit", "q"}
# 기본 대화 시간 제한 (초)
DEFAULT_TIME_LIMIT_SECONDS = 240

def _sanitize_text(value: str) -> str:
    """텍스트의 인코딩 문제를 방지하기 위해 정제합니다."""
    return value.encode("utf-8", "ignore").decode("utf-8")

def _prompt_input(label: str, timeout_seconds: int) -> str:
    """시간 제한이 있는 텍스트 입력을 처리합니다."""
    while True:
        if timeout_seconds <= 0:
            raise TimeoutError
        sys.stdout.write(label)
        sys.stdout.flush()
        # 입력 대기 (타임아웃 설정)
        ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if not ready:
            raise TimeoutError
        value = sys.stdin.readline().strip()
        if value.lower() in EXIT_TOKENS:
            raise KeyboardInterrupt
        if value:
            return value

def _timeout_reached(start_time: float, limit_seconds: int) -> bool:
    """시간 제한에 도달했는지 확인합니다."""
    return time.monotonic() - start_time >= limit_seconds

def _choose_input_mode() -> str:
    """입력 방식(음성 또는 채팅)을 선택합니다."""
    raw_mode = os.getenv("SCENARIO_INPUT_MODE", "").strip().lower()
    if raw_mode in {"voice", "1"}:
        return "1"
    if raw_mode in {"chat", "2"}:
        return "2"
    print("입력 방식을 선택하세요:")
    print("1) 음성 (Voice)")
    print("2) 채팅 (Chat)")
    while True:
        choice = input("선택: ").strip()
        if choice in {"1", "2"}:
            return choice
        print("1 또는 2를 입력해주세요.")

def _handle_timeout(scenario) -> None:
    """시간 초과 시 처리 로직입니다."""
    print(f"Sarah: {scenario.fail_message}")
    print("Sarah가 다음 회의를 위해 자리를 뜹니다.")

def _prompt_voice_input(timeout_seconds: int) -> str:
    """음성 입력을 텍스트로 변환하여 가져옵니다."""
    language_code = os.getenv("SCENARIO_VOICE_LANGUAGE", "en-US")
    sample_rate = int(os.getenv("SCENARIO_VOICE_SAMPLE_RATE", "16000"))
    record_seconds = int(os.getenv("SCENARIO_VOICE_RECORD_SECONDS", "5"))
    audio_path = os.getenv("SCENARIO_VOICE_AUDIO_PATH")
    max_seconds = max(1, timeout_seconds - 1)
    record_seconds = max(1, min(record_seconds, max_seconds))

    if audio_path:
        print(f"오디오 파일 변환 중: {audio_path}")
    else:
        print(f"{record_seconds}초 동안 녹음합니다...")
    
    transcript = capture_and_transcribe(
        duration_seconds=record_seconds,
        sample_rate=sample_rate,
        language_code=language_code,
        audio_path=audio_path,
    )
    transcript = transcript.strip()
    if not transcript:
        print("음성이 감지되지 않았습니다. 텍스트로 입력해주세요.")
        return _prompt_input("입력: ", timeout_seconds)
    print(f"나: {transcript}")
    return transcript

async def _run_evaluator(transcript: list[str]) -> str:
    """평가 에이전트를 통해 대화 내용을 분석합니다."""
    eval_runner, eval_session = await build_eval_runtime()
    safe_transcript = [_sanitize_text(line) for line in transcript]
    eval_prompt = build_eval_prompt("standup", safe_transcript)
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

def _score_to_rank(score_25: int) -> str | None:
    """점수를 랭크로 변환합니다."""
    if score_25 >= 20: return "S"
    if score_25 >= 16: return "A"
    if score_25 >= 12: return "B"
    if score_25 >= 8:  return "C"
    if score_25 >= 1:  return "F"
    return None

def _extract_score(text: str) -> tuple[int, int] | None:
    """텍스트에서 점수 정보를 추출합니다."""
    match = re.search(r"Score:\s*([0-9]+)\s*/\s*([0-9]+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))

async def main() -> int:
    """에이전트 시나리오 실행 메인 비동기 함수입니다."""
    scenario = get_scenario()
    print(scenario.title)
    print(scenario.background)
    print(scenario.npc_state)
    print(scenario.items)
    print("모든 대화는 영어로 진행됩니다.")

    input_mode = _choose_input_mode()
    input_label = "입력: "
    if input_mode == "1":
        print("음성 모드가 선택되었습니다.")

    affinity = 0 # 호감도
    trust = 0    # 신뢰도
    final_rank = None
    completed = False
    timed_out = False
    exited_early = False
    transcript: list[str] = []
    time_limit = int(os.getenv("SCENARIO_TIME_LIMIT_SECONDS", DEFAULT_TIME_LIMIT_SECONDS))
    start_time = time.monotonic()

    try:
        # 각 스테이지별로 대화를 진행합니다.
        for stage in scenario.stages:
            remaining = int(time_limit - (time.monotonic() - start_time))
            if remaining <= 0:
                timed_out = True
                _handle_timeout(scenario)
                break
            print()
            print(f"== {stage.title} ==")
            print(stage.prompt)
            try:
                if input_mode == "1":
                    user_input = _sanitize_text(_prompt_voice_input(remaining))
                else:
                    user_input = _sanitize_text(_prompt_input(input_label, remaining))
            except TimeoutError:
                timed_out = True
                _handle_timeout(scenario)
                break
            transcript.append(f"You: {user_input}")

            # 사용자의 입력에 따른 NPC의 반응을 결정합니다.
            branch = stage.match(user_input)
            affinity += branch.affinity_delta
            trust += branch.trust_delta

            print(f"Sarah: {branch.response}")
            transcript.append(f"Sarah: {branch.response}")

            # 잘못된 대답을 했을 경우 복구 기회를 줄지 확인합니다.
            if stage.recovery and stage.recovery.should_offer(branch):
                print("Sarah의 표정이 안 좋습니다. 어떻게 대답하시겠습니까?")
                remaining = int(time_limit - (time.monotonic() - start_time))
                if remaining <= 0:
                    timed_out = True
                    _handle_timeout(scenario)
                    break
                try:
                    if input_mode == "1":
                        recovery_input = _sanitize_text(_prompt_voice_input(remaining))
                    else:
                        recovery_input = _sanitize_text(
                            _prompt_input(input_label, remaining)
                        )
                except TimeoutError:
                    timed_out = True
                    _handle_timeout(scenario)
                    break
                transcript.append(f"You: {recovery_input}")
                recovery_branch = stage.recovery.match(recovery_input)
                if recovery_branch:
                    affinity += recovery_branch.affinity_delta
                    trust += recovery_branch.trust_delta
                    print(f"Sarah: {recovery_branch.response}")
                    transcript.append(f"Sarah: {recovery_branch.response}")
                elif branch.ends_conversation:
                    print("Sarah: 대화가 종료되었습니다.")
                    final_rank = "F"
                    break

            if branch.ends_conversation:
                print("Sarah: 대화가 종료되었습니다.")
                final_rank = "F"
                break

            if stage.key == "STAGE_4":
                final_rank = branch.final_rank or "B"
                completed = True
    except KeyboardInterrupt:
        exited_early = True

    print()
    if completed:
        print(f"Sarah: {scenario.success_message}")
    if exited_early:
        print("종료 중입니다.")
    
    # 대화 종료 후 평가 세션 시작
    print("=== 평가 (Evaluation) ===")
    eval_reply = await _run_evaluator(transcript)
    print(eval_reply)
    score_data = _extract_score(eval_reply)
    score_25 = None
    if score_data:
        score_value, score_max = score_data
        if score_max == 25:
            score_25 = score_value
        elif score_max == 5:
            score_25 = score_value * 5
    
    rank_from_score = _score_to_rank(score_25) if score_25 is not None else None
    if rank_from_score:
        final_rank = rank_from_score
    if final_rank is None:
        final_rank = "B" if completed else "F"
    
    print(f"최종 랭크: {final_rank}")
    print("대화가 모두 종료되었습니다.")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
