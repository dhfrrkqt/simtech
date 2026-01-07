from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Action:
    key: str
    title: str
    description: str
    runner: Callable[[], int]


def _run_social_standup() -> int:
    from curator_agent.main import main as curator_main
    import sys

    original_args = sys.argv[:]
    sys.argv = [original_args[0], "standup"]
    try:
        if asyncio.iscoroutinefunction(curator_main):
            return asyncio.run(curator_main())
        return curator_main()
    finally:
        sys.argv = original_args


def _run_evaluator() -> int:
    from evaluator_agent.main import main as evaluator_main

    return evaluator_main()


ACTIONS: list[Action] = [
    Action(
        key="1",
        title="Startup Standup 2.0 scenario",
        description="Talk with Sarah at the SusHi Tech Tokyo 2026 networking lounge.",
        runner=_run_social_standup,
    ),
    Action(
        key="2",
        title="Conversation evaluation",
        description="Evaluate a conversation log.",
        runner=_run_evaluator,
    ),
]
