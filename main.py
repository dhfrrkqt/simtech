from agent_executor import run_action


def main() -> int:
    print("Startup Standup 2.0: The Bottleneck Breaker")
    print("There is 1 scenario available. Starting now.")
    return run_action("1")


if __name__ == "__main__":
    raise SystemExit(main())
