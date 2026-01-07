from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Branch:
    """대화의 특정 분기점을 정의하는 클래스입니다."""
    key: str                # 분기점 고유 키
    intent: str               # 제작자가 의도한 대화의 성격 (예: 공감, 공격적 등)
    keywords: tuple[str, ...] # 이 분기점으로 진입하게 만드는 키워드 목록
    response: str             # NPC의 응답 텍스트
    effect: str               # 게임 내 효과 설명 (텍스트)
    affinity_delta: int = 0    # 호감도 변화량
    trust_delta: int = 0       # 신뢰도 변화량
    ends_conversation: bool = False # 대화 종료 여부
    final_rank: str | None = None   # 스테이지 종료 시 부여될 랭크

@dataclass(frozen=True)
class Recovery:
    """실수를 만회할 수 있는 복구 시나리오를 정의합니다."""
    keywords: tuple[str, ...] # 복구를 위한 키워드
    response: str             # 복구 성공 시 NPC의 응답
    affinity_delta: int = 0    # 복구 시 호감도 변화
    trust_delta: int = 0       # 복구 시 신뢰도 변화

@dataclass(frozen=True)
class RecoveryRule:
    """실수한 분기점에서 복구 모드를 제안하고 처리하는 규칙입니다."""
    trigger_keys: tuple[str, ...] # 이 분기점들에 도달했을 때 복구 기회를 제공함
    recovery: Recovery             # 실제 복구 내용

    def should_offer(self, branch: Branch) -> bool:
        """현재 분기가 복구 기회를 줄 대상인지 확인합니다."""
        return branch.key in self.trigger_keys

    def match(self, text: str) -> Recovery | None:
        """사용자의 입력이 복구 키워드와 일치하는지 확인합니다."""
        normalized = text.strip().lower()
        if any(keyword.lower() in normalized for keyword in self.recovery.keywords):
            return self.recovery
        return None

@dataclass(frozen=True)
class Stage:
    """대화의 개별 단계를 정의하는 클래스입니다."""
    key: str                   # 스테이지 키
    title: str                 # 스테이지 제목
    prompt: str                # 사용자에게 보여줄 상황 설명 또는 질문
    branches: tuple[Branch, ...] # 해당 스테이지에서 가능한 분기 목록
    default_branch: str        # 키워드 매칭 실패 시 사용할 기본 분기 키
    recovery: RecoveryRule | None = None # 복구 규칙 (옵션)

    def match(self, text: str) -> Branch:
        """사용자의 입력을 분석하여 적절한 분기를 반환합니다."""
        normalized = text.strip().lower()
        # 키워드 매칭 시도
        for branch in self.branches:
            if any(keyword.lower() in normalized for keyword in branch.keywords):
                return branch
        # 매칭 실패 시 기본 분기 반환
        for branch in self.branches:
            if branch.key == self.default_branch:
                return branch
        return self.branches[0]

@dataclass(frozen=True)
class StandupScenario:
    """전체 시나리오 정보를 담고 있는 클래스입니다."""
    key: str
    title: str
    description: str
    background: str
    npc_state: str
    items: str
    success_message: str # 시나리오 성공 시 메시지
    fail_message: str    # 시나리오 실패 시 메시지
    stages: tuple[Stage, ...] # 시나리오를 구성하는 스테이지들

# --- 실제 시나리오 데이터 (STAGE_1 ~ STAGE_4) ---

STAGE_1 = Stage(
    key="STAGE_1",
    title="접근 단계 (The Approach)",
    prompt=(
        "SusHi Tech Tokyo 2026 스타트업 라운지에서 붐비는 자리에 빈 의자 하나를 발견했습니다. "
        "앉아도 되는지 물어보시겠습니까?"
    ),
    branches=(
        Branch(
            key="1-A",
            intent="공감 (최고)",
            keywords=("battlefield", "war zone", "shelter", "quiet", "hectic"),
            response=(
                "(미소 지으며) 네, 정말 전쟁터 같죠. 앉으세요. 우리 모두 오늘 고생이 많네요."
            ),
            effect="호감도 +10, 긴장이 풀림",
            affinity_delta=10,
        ),
        Branch(
            key="1-B",
            intent="일반적인 질문 (보통)",
            keywords=("seat", "taken", "empty", "sit", "here"),
            response="(한숨) 비어있어요. 앉으세요. 그냥 따라가는 것만으로도 벅차네요.",
            effect="호감도 0, 대화 시작",
        ),
        Branch(
            key="1-C",
            intent="무례함 (나쁨)",
            keywords=("move", "my seat", "sit down", "save it"),
            response="(인상을 찌푸리며) 저기요, 누구신데 이러시죠? 다시 하세요.",
            effect="대화 종료 (GAME OVER)",
            ends_conversation=True,
        ),
    ),
    default_branch="1-B",
    recovery=RecoveryRule(
        trigger_keys=("1-B", "1-C"),
        recovery=Recovery(
            keywords=("understood", "sorry", "my bad", "apologies", "back off", "retreat"),
            response=(
                "알겠습니다. (한숨) 10분 정도 뒤라면 대화가 가능할 것 같네요. "
                "죄송해요, 힘든 하루여서요."
            ),
            affinity_delta=5,
        ),
    ),
)

STAGE_2 = Stage(
    key="STAGE_2",
    title="아이스 브레이킹 (Ice Breaking)",
    prompt="Sarah에게 첫 인사를 건넵니다. 무엇이라고 하시겠습니까?",
    branches=(
        Branch(
            key="2-1",
            intent="선물 (최고)",
            keywords=("candy", "sweet", "sugar", "gift", "snack"),
            response=(
                "(웃음) 사탕을 가져오셨다구요? 예상치 못한 친절이네요. 좋은 시작입니다."
            ),
            effect="호감도 +30, 질문을 허락함",
            affinity_delta=30,
        ),
        Branch(
            key="2-2",
            intent="관찰 (좋음)",
            keywords=("coffee", "caffeine", "cup", "espresso"),
            response="(컵을 쳐다보며) 벌써 네 잔째네요. 정말 열심히 버티고 계시는군요.",
            effect="호감도 +10, 유대감 형성",
            affinity_delta=10,
        ),
        Branch(
            key="2-3",
            intent="공감 (안전함)",
            keywords=("crowd", "noise", "busy", "energy"),
            response=(
                "여기는 정말 시끄럽네요. 말소리 듣기도 힘들죠? 여기까지 오느라 고생하셨어요."
            ),
            effect="호감도 +5, 무난한 대화",
            affinity_delta=5,
        ),
        Branch(
            key="2-5",
            intent="칭찬 (위험)",
            keywords=("style", "sharp", "professional", "look"),
            response=(
                "(미소 지으며) 고마워요. 빈말인 거 알겠지만 접수해두죠. 전 그냥 오늘 살아남으려고 노력 중이에요."
            ),
            effect="호감도 +5, 약간의 어색함",
            affinity_delta=5,
        ),
        Branch(
            key="2-6",
            intent="날씨 (지루함)",
            keywords=("weather", "snow", "cold", "finland"),
            response="(무미건조하게) 네, 춥네요. 그래서, 여기엔 왜 오셨죠?",
            effect="호감도 0, 곧장 업무 이야기로",
        ),
        Branch(
            key="2-7",
            intent="무례 (나쁨)",
            keywords=("old", "tired", "exhausted"),
            response=(
                "(딱딱하게) 실례지만, 좀 사적인 질문이네요. 공적인 자리를 유지하죠."
            ),
            effect="호감도 -20, 긴장 고조",
            affinity_delta=-20,
        ),
        Branch(
            key="2-8",
            intent="강한 압박 (최악)",
            keywords=("pitch", "listen", "idea", "startup"),
            response="(말을 자르며) 저기요, 전 지금 10초도 없어요. 가보세요.",
            effect="호감도 -30, 거절",
            affinity_delta=-30,
            ends_conversation=True,
        ),
    ),
    default_branch="2-3",
)

STAGE_3 = Stage(
    key="STAGE_3",
    title="비즈니스 제안 (The Pitch)",
    prompt="Sarah가 묻습니다. '그래서, 무엇을 만들고 계시죠?'",
    branches=(
        Branch(
            key="3-1",
            intent="통찰 (최고)",
            keywords=("psychology", "non-verbal", "eye contact", "behavior"),
            response=(
                "저희는 투자자와의 대화에서 비언어적 신호를 분석해주는 AI 코칭 서비스를 만듭니다. "
                "사람이 놓치기 쉬운 부분을 잡아내죠."
            ),
            effect="신뢰도 +30, 전문가로 인정받음",
            trust_delta=30,
        ),
        Branch(
            key="3-2",
            intent="비유 (좋음)",
            keywords=("simulator", "pilot", "training", "practice"),
            response=(
                "투자자 미팅을 위한 비행 시뮬레이터라고 생각하시면 됩니다. "
                "실전처럼 느껴질 때까지 연습할 수 있죠."
            ),
            effect="신뢰도 +20, 명확한 전달",
            trust_delta=20,
        ),
        Branch(
            key="3-3",
            intent="문제 해결 (좋음)",
            keywords=("gen z", "communication", "gap", "text"),
            response=(
                "Z세대는 면접에서 시선 처리를 어려워합니다. 저희는 그 소통의 간극을 빠르게 매워줍니다."
            ),
            effect="신뢰도 +20, 문제 공감",
            trust_delta=20,
        ),
        Branch(
            key="3-4",
            intent="니치 시장 (집중)",
            keywords=("therapy", "autism", "anxiety", "clinical"),
            response="불안 장애와 자폐증 지원부터 시작합니다. 집중적인 디지털 치료제 영역이죠.",
            effect="신뢰도 +15, 니치 포커스",
            trust_delta=15,
        ),
        Branch(
            key="3-5",
            intent="기술 중심 (무난)",
            keywords=("llm", "latency", "model", "vision ai"),
            response="(고개를 끄덕이며) 기술은 괜찮네요. 비즈니스 모델은 구체적으로 무엇인가요?",
            effect="신뢰도 +5, 약간의 지루함",
            trust_delta=5,
        ),
        Branch(
            key="3-6",
            intent="타사 비교 (방어적)",
            keywords=("chatgpt", "zoom", "better", "competition"),
            response=(
                "차별화가 중요하죠. 남들이 나쁘다는 얘기 말고 그쪽만의 강점을 말해주세요."
            ),
            effect="신뢰도 0, 약간의 거부감",
        ),
        Branch(
            key="3-7",
            intent="모호함 (위험)",
            keywords=("happy", "world", "dream", "vision"),
            response="(미소 지으며) 비전은 좋네요. 하지만 구체적인 비즈니스 모델이 뭔가요?",
            effect="신뢰도 -10, 회의적",
            trust_delta=-10,
        ),
        Branch(
            key="3-8",
            intent="과장 (최악)",
            keywords=("unicorn", "money", "rich", "billion"),
            response="(인상을 쓰며) 너무 큰 주장이네요. 실체를 보여주지 않으면 여기서 끝입니다.",
            effect="신뢰도 -30, 신뢰 깨짐",
            trust_delta=-30,
        ),
    ),
    default_branch="3-7",
)

STAGE_4 = Stage(
    key="STAGE_4",
    title="마무리 단계 (The Closing)",
    prompt="Sarah가 일정을 확인합니다. 이제 대화를 마무리할 시간입니다. 어떻게 마무리하시겠습니까?",
    branches=(
        Branch(
            key="4-A",
            intent="QR 데모 (최고)",
            keywords=("card", "qr", "scan", "instant", "demo"),
            response=(
                "지금 바로 이메일로 간단한 데모 링크를 보내드릴 수 있습니다. "
                "보시고 유용하다면 정식 미팅을 잡고 싶습니다."
            ),
            effect="S 랭크 후보",
            final_rank="S",
        ),
        Branch(
            key="4-B",
            intent="연락처 요청 (보통)",
            keywords=("email", "contact", "later", "send"),
            response="회사 소개서와 자료를 이메일로 보내드리겠습니다. 귀한 시간 감사드립니다.",
            effect="B 랭크 후보",
            final_rank="B",
        ),
        Branch(
            key="4-C",
            intent="작별 인사 (나쁨)",
            keywords=("bye", "thanks", "go", "see you"),
            response="네, 알겠습니다. 다음에 뵙죠.",
            effect="F 랭크 후보",
            ends_conversation=True,
            final_rank="F",
        ),
    ),
    default_branch="4-B",
)

STANDUP = StandupScenario(
    key="standup",
    title="Startup Standup 2.0: The Bottleneck Breaker",
    description="SusHi Tech Tokyo 2026 스타트업 라운지에서 Sarah를 만납니다.",
    background="배경: SusHi Tech Tokyo 2026 스타트업 라운지",
    npc_state="NPC: Sarah (벤처 캐피털리스트) - 상태: 매우 바쁨, 경계심 높음",
    items="아이템: 사탕, QR 명함",
    success_message="좋습니다. 흥미롭군요. 정식 미팅에서 더 자세히 이야기해 봅시다.",
    fail_message=(
        "죄송하지만 이제 가봐야겠네요. 나중에 기회가 되면 다시 이야기하죠."
    ),
    stages=(STAGE_1, STAGE_2, STAGE_3, STAGE_4),
)

def get_scenario() -> StandupScenario:
    """현재 활성화된 시나리오 객체를 반환합니다."""
    return STANDUP
