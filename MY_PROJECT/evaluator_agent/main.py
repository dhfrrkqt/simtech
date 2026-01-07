import asyncio

from evaluator_agent.agent_executor import build_message, build_runtime
from evaluator_agent.scenarios import build_eval_prompt

# 종료 명령어
EXIT_TOKENS = {"exit", "quit", "q"}

async def _run_eval(conversation: str) -> int:
    """대화 내용을 평가 에이전트에게 보내 결과를 가져옵니다."""
    try:
        # 에이전트 실행 환경 빌드
        runner, session = await build_runtime()
    except Exception as exc:
        print(f"평가 에이전트 초기화 실패: {exc}")
        return 1

    # 평가용 프롬프트 생성
    prompt = build_eval_prompt("standup", conversation.splitlines())
    try:
        # 에이전트 비동기 실행 및 응답 수집
        events = runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=build_message(prompt),
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
        reply = "".join(chunks)
    except Exception as exc:
        print(f"평가 중 오류 발생: {exc}")
        return 1
    finally:
        await runner.close()

    # 최종 평가 결과 출력
    print(reply)
    return 0

def main() -> int:
    """평가 에이전트 메인 함수 (콘솔 입력 처리)"""
    print("평가 에이전트가 준비되었습니다. 평가할 대화 내용을 붙여넣으세요.")
    print("빈 줄을 입력하면 입력을 마치고, 'exit'를 입력하면 종료합니다.")

    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in EXIT_TOKENS:
            return 0
        if line.strip() == "":
            if not lines:
                continue
            break
        lines.append(line)

    conversation = "\n".join(lines)
    # 비동기로 평가 로직 실행
    return asyncio.run(_run_eval(conversation))

if __name__ == "__main__":
    raise SystemExit(main())
