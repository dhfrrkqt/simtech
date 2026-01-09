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


EXIT_TOKENS = {"exit", "quit", "q"}
DEFAULT_TIME_LIMIT_SECONDS = 240


def _sanitize_text(value: str) -> str:
    return value.encode("utf-8", "ignore").decode("utf-8")


def _prompt_input(label: str, timeout_seconds: int) -> str:
    while True:
        if timeout_seconds <= 0:
            raise TimeoutError
        sys.stdout.write(label)
        sys.stdout.flush()
        ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if not ready:
            raise TimeoutError
        value = sys.stdin.readline().strip()
        if value.lower() in EXIT_TOKENS:
            raise KeyboardInterrupt
        if value:
            return value


def _timeout_reached(start_time: float, limit_seconds: int) -> bool:
    return time.monotonic() - start_time >= limit_seconds


def _choose_input_mode() -> str:
    raw_mode = os.getenv("SCENARIO_INPUT_MODE", "").strip().lower()
    if raw_mode in {"voice", "1"}:
        return "1"
    if raw_mode in {"chat", "2"}:
        return "2"
    print("Select input method:")
    print("1) Voice")
    print("2) Chat")
    while True:
        choice = input("Choice: ").strip()
        if choice in {"1", "2"}:
            return choice
        print("Please enter 1 or 2.")


def _speak(text: str) -> None:
    if os.getenv("TTS_ENABLED", "").lower() != "true":
        return
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass


def _handle_timeout(scenario) -> None:
    print(f"Sarah: {scenario.fail_message}")
    _speak(scenario.fail_message)
    print("Sarah leaves her seat to head to the next meeting.")


def _prompt_voice_input(timeout_seconds: int) -> str:
    language_code = os.getenv("SCENARIO_VOICE_LANGUAGE", "en-US")
    sample_rate = int(os.getenv("SCENARIO_VOICE_SAMPLE_RATE", "16000"))
    record_seconds = int(os.getenv("SCENARIO_VOICE_RECORD_SECONDS", "5"))
    audio_path = os.getenv("SCENARIO_VOICE_AUDIO_PATH")
    max_seconds = max(1, timeout_seconds - 1)
    record_seconds = max(1, min(record_seconds, max_seconds))

    if audio_path:
        print(f"Transcribing audio file: {audio_path}")
    else:
        print(f"Recording for {record_seconds} seconds...")
    transcript = capture_and_transcribe(
        duration_seconds=record_seconds,
        sample_rate=sample_rate,
        language_code=language_code,
        audio_path=audio_path,
    )
    transcript = transcript.strip()
    if not transcript:
        print("No speech detected. Please type your response.")
        return _prompt_input("Type: ", timeout_seconds)
    print(f"You: {transcript}")
    return transcript


async def _run_evaluator(transcript: list[str]) -> str:
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


async def main() -> int:
    scenario = get_scenario()
    print(scenario.title)
    print(scenario.background)
    print(scenario.npc_state)
    print(scenario.items)
    print("All conversations are in English.")

    input_mode = _choose_input_mode()
    input_label = "Type: "
    if input_mode == "1":
        print("Voice mode selected.")

    affinity = 0
    trust = 0
    final_rank = None
    completed = False
    timed_out = False
    exited_early = False
    transcript: list[str] = []
    time_limit = int(os.getenv("SCENARIO_TIME_LIMIT_SECONDS", DEFAULT_TIME_LIMIT_SECONDS))
    start_time = time.monotonic()

    try:
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

            branch = stage.match(user_input)
            affinity += branch.affinity_delta
            trust += branch.trust_delta

            print(f"Sarah: {branch.response}")
            _speak(branch.response)
            transcript.append(f"Sarah: {branch.response}")

            if stage.recovery and stage.recovery.should_offer(branch):
                print("Sarah looks cold. How do you respond?")
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
                    _speak(recovery_branch.response)
                    transcript.append(f"Sarah: {recovery_branch.response}")
                elif branch.ends_conversation:
                    print("Sarah: The conversation has ended.")
                    _speak("The conversation has ended.")
                    final_rank = "F"
                    break

            if branch.ends_conversation:
                print("Sarah: The conversation has ended.")
                _speak("The conversation has ended.")
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
        _speak(scenario.success_message)
    if exited_early:
        print("Exiting.")
    print("=== Evaluation ===")
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
    print(f"Final rank: {final_rank}")
    print("Conversation ended.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
