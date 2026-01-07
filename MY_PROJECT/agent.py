from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Action:
    """에이전트가 수행할 수 있는 개별 행동(시나리오 등)을 정의하는 클래스입니다."""
    key: str          # 행동 선택 번호
    title: str        # 행동의 제목
    description: str  # 행동에 대한 간략한 설명
    runner: Callable[[], int] # 실행할 함수

def _run_social_standup() -> int:
    """스타트업 네트워킹 시나리오를 실행하는 내부 함수입니다."""
    from curator_agent.main import main as curator_main
    import sys

    # 명령어 인자를 조정하여 시나리오를 실행합니다.
    original_args = sys.argv[:]
    sys.argv = [original_args[0], "standup"]
    try:
        # 비동기 함수인 경우 asyncio.run으로 실행합니다.
        if asyncio.iscoroutinefunction(curator_main):
            return asyncio.run(curator_main())
        return curator_main()
    finally:
        # 변경했던 인자를 원래대로 복구합니다.
        sys.argv = original_args

def _run_evaluator() -> int:
    """대화 평가 에이전트를 실행하는 내부 함수입니다."""
    from evaluator_agent.main import main as evaluator_main
    return evaluator_main()

# 사용자가 선택할 수 있는 행동들의 목록입니다.
ACTIONS: list[Action] = [
    Action(
        key="1",
        title="Startup Standup 2.0 시나리오",
        description="SLUSH 2025 네트워킹 라운지에서 Sarah와 대화하며 기회를 잡으세요.",
        runner=_run_social_standup,
    ),
    Action(
        key="2",
        title="대화 내용 평가",
        description="기존 대화 기록을 분석하고 평가합니다.",
        runner=_run_evaluator,
    ),
]
