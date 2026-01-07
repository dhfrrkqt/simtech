from agent_executor import run_action

def main() -> int:
    """프로그램의 메인 진입점입니다."""
    print("Startup Standup 2.0: The Bottleneck Breaker")
    print("사용 가능한 시나리오가 1개 있습니다. 지금 시작합니다.")
    # 기본적으로 '1'번 시나리오(스타트업 스탠드업)를 실행합니다.
    return run_action("1")

if __name__ == "__main__":
    # main 함수를 실행하고 결과 코드를 시스템에 반환합니다.
    raise SystemExit(main())
