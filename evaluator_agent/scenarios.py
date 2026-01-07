from __future__ import annotations


STANDUP_RUBRIC = (
    "Scenario: Startup Standup 2.0\n"
    "- Intent flow: approach -> ice breaking -> pitch -> closing\n"
    "- Evaluate whether choices affect affinity/trust/rank.\n"
    "- If the reply uses formal endings (e.g., polite forms), treat it as formal.\n"
    "- Do not penalize consistent formal tone; reward it.\n"
    "- Respond only in English. No Korean or other languages.\n"
    "Output: 1-2 sentence summary + 'Score: X/5'"
)


def build_eval_prompt(scenario_key: str, transcript: list[str]) -> str:
    return (
        "Please evaluate the following conversation. Respond only in English.\n\n"
        + "\n".join(transcript)
        + "\n\n"
        + STANDUP_RUBRIC
    )
