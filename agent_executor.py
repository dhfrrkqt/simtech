from agent import Action, ACTIONS


def list_actions() -> list[Action]:
    return ACTIONS


def get_action(choice: str) -> Action | None:
    for action in ACTIONS:
        if action.key == choice:
            return action
    return None


def run_action(choice: str) -> int:
    action = get_action(choice)
    if not action:
        print("Invalid selection.")
        return 1
    return action.runner()
