import asyncio

from evaluator_agent.agent_executor import build_message, build_runtime
from evaluator_agent.scenarios import build_eval_prompt


EXIT_TOKENS = {"exit", "quit", "q"}


async def _run_eval(conversation: str) -> int:
    try:
        runner, session = await build_runtime()
    except Exception as exc:
        print(f"Failed to initialize evaluator agent: {exc}")
        return 1

    prompt = build_eval_prompt("standup", conversation.splitlines())
    try:
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
        print(f"Evaluator error: {exc}")
        return 1
    finally:
        await runner.close()

    print(reply)
    return 0


def main() -> int:
    print("Evaluator agent is ready. Paste the conversation to evaluate.")
    print("Enter a blank line to finish, or type 'exit' to quit.")

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
    return asyncio.run(_run_eval(conversation))


if __name__ == "__main__":
    raise SystemExit(main())
