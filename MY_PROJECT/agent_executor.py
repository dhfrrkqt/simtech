from agent import Action, ACTIONS

def list_actions() -> list[Action]:
    """등록된 모든 행동 목록을 반환합니다."""
    return ACTIONS

def get_action(choice: str) -> Action | None:
    """사용자가 입력한 번호에 해당하는 행동을 찾아 반환합니다."""
    for action in ACTIONS:
        if action.key == choice:
            return action
    return None

def run_action(choice: str) -> int:
    """지정된 번호의 행동을 직접 실행합니다."""
    action = get_action(choice)
    if not action:
        print("잘못된 선택입니다.")
        return 1
    # 해당 행동에 등록된 runner 함수를 호출합니다.
    return action.runner()
