from __future__ import annotations

# 평가에 사용할 기준(루브릭)을 정의합니다.
STANDUP_RUBRIC = (
    "시나리오: 스타트업 스탠드업 2.0\n"
    "- 대화 흐름 평가: 접근 -> 아이스 브레이킹 -> 피칭 -> 마무리\n"
    "- 선택지가 호감도/신뢰도/랭크에 적절한 영향을 미쳤는지 평가.\n"
    "- 존댓말(격식 있는 표현)을 사용했다면 긍정적으로 평가.\n"
    "- 일관된 격식 있는 톤을 장려함.\n"
    "- 결과는 반드시 영어로만 답변할 것.\n"
    "출력 형식: 1-2문장의 요약 + 'Score: X/5'"
)

def build_eval_prompt(scenario_key: str, transcript: list[str]) -> str:
    """평가 에이전트에게 보낼 전체 프롬프트를 구성합니다."""
    return (
        "다음 대화를 평가해 주세요. 영어로만 답변해 주세요.\n\n"
        + "\n".join(transcript)
        + "\n\n"
        + STANDUP_RUBRIC
    )
