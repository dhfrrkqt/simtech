from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Branch:
    key: str
    intent: str
    keywords: tuple[str, ...]
    response: str
    effect: str
    affinity_delta: int = 0
    trust_delta: int = 0
    ends_conversation: bool = False
    final_rank: str | None = None


@dataclass(frozen=True)
class Recovery:
    keywords: tuple[str, ...]
    response: str
    affinity_delta: int = 0
    trust_delta: int = 0


@dataclass(frozen=True)
class RecoveryRule:
    trigger_keys: tuple[str, ...]
    recovery: Recovery

    def should_offer(self, branch: Branch) -> bool:
        return branch.key in self.trigger_keys

    def match(self, text: str) -> Recovery | None:
        normalized = text.strip().lower()
        if any(keyword.lower() in normalized for keyword in self.recovery.keywords):
            return self.recovery
        return None


@dataclass(frozen=True)
class Stage:
    key: str
    title: str
    prompt: str
    branches: tuple[Branch, ...]
    default_branch: str
    recovery: RecoveryRule | None = None

    def match(self, text: str) -> Branch:
        normalized = text.strip().lower()
        for branch in self.branches:
            if any(keyword.lower() in normalized for keyword in branch.keywords):
                return branch
        for branch in self.branches:
            if branch.key == self.default_branch:
                return branch
        return self.branches[0]


@dataclass(frozen=True)
class StandupScenario:
    key: str
    title: str
    description: str
    background: str
    npc_state: str
    items: str
    success_message: str
    fail_message: str
    stages: tuple[Stage, ...]


STAGE_1 = Stage(
    key="STAGE_1",
    title="The Approach",
    prompt=(
        "At the SusHi Tech Tokyo 2026 startup lounge, you spot an empty seat in a crowded area. "
        "Do you ask to sit?"
    ),
    branches=(
        Branch(
            key="1-A",
            intent="Empathy (Best)",
            keywords=("battlefield", "war zone", "shelter", "quiet", "hectic"),
            response=(
                "(smiles) Yeah, it is a war zone. Sure, take a seat. We are all in the "
                "trenches today."
            ),
            effect="Affinity +10, guard drops",
            affinity_delta=10,
        ),
        Branch(
            key="1-B",
            intent="Simple question (Normal)",
            keywords=("seat", "taken", "empty", "sit", "here"),
            response="(sigh) It is free. Go ahead. Just keeping up is a lot.",
            effect="Affinity 0, conversation opens",
        ),
        Branch(
            key="1-C",
            intent="Pushy (Bad)",
            keywords=("move", "my seat", "sit down", "save it"),
            response="(frowns) Hey. Who do you think you are? Let's reset.",
            effect="GAME OVER",
            ends_conversation=True,
        ),
    ),
    default_branch="1-B",
    recovery=RecoveryRule(
        trigger_keys=("1-B", "1-C"),
        recovery=Recovery(
            keywords=("understood", "sorry", "my bad", "apologies", "back off", "retreat"),
            response=(
                "Okay. (sigh) If you give me 10 minutes, I can talk later. "
                "Sorry, long day."
            ),
            affinity_delta=5,
        ),
    ),
)

STAGE_2 = Stage(
    key="STAGE_2",
    title="Ice Breaking",
    prompt="You say your first line to Sarah. What do you say?",
    branches=(
        Branch(
            key="2-1",
            intent="Gift (Best)",
            keywords=("candy", "sweet", "sugar", "gift", "snack"),
            response=(
                "(laughs) You brought candy? That is unexpectedly kind. Nice icebreaker."
            ),
            effect="Affinity +30, she invites questions",
            affinity_delta=30,
        ),
        Branch(
            key="2-2",
            intent="Observation (Good)",
            keywords=("coffee", "caffeine", "cup", "espresso"),
            response="(glances at cup) Fourth cup already. You are really powering through.",
            effect="Affinity +10, small rapport",
            affinity_delta=10,
        ),
        Branch(
            key="2-3",
            intent="Empathy (Safe)",
            keywords=("crowd", "noise", "busy", "energy"),
            response=(
                "This place is loud. Hard to hear anything, right? Thanks for braving it."
            ),
            effect="Affinity +5, safe entry",
            affinity_delta=5,
        ),
        Branch(
            key="2-5",
            intent="Compliment (Risky)",
            keywords=("style", "sharp", "professional", "look"),
            response=(
                "(smiles) Thanks. Flattery noted. I am just trying to survive the day."
            ),
            effect="Affinity +5, slight awkwardness",
            affinity_delta=5,
        ),
        Branch(
            key="2-6",
            intent="Weather (Boring)",
            keywords=("weather", "snow", "cold", "finland"),
            response="(dry) Yeah, it is cold. So, what are you here for?",
            effect="Affinity 0, back to business",
        ),
        Branch(
            key="2-7",
            intent="Insult (Bad)",
            keywords=("old", "tired", "exhausted"),
            response=(
                "(flat) Excuse me? That is a bit personal. Let's keep it professional."
            ),
            effect="Affinity -20, tension",
            affinity_delta=-20,
        ),
        Branch(
            key="2-8",
            intent="Hard pitch (Worst)",
            keywords=("pitch", "listen", "idea", "startup"),
            response="(cuts in) I have ten seconds. Go.",
            effect="Affinity -30, shut down",
            affinity_delta=-30,
            ends_conversation=True,
        ),
    ),
    default_branch="2-3",
)

STAGE_3 = Stage(
    key="STAGE_3",
    title="The Pitch",
    prompt="Sarah asks, 'So, what are you building?'",
    branches=(
        Branch(
            key="3-1",
            intent="Insight (Best)",
            keywords=("psychology", "non-verbal", "eye contact", "behavior"),
            response=(
                "We build AI that coaches founders on nonverbal signals in investor "
                "conversations. It catches what people miss."
            ),
            effect="Trust +30, expert validation",
            trust_delta=30,
        ),
        Branch(
            key="3-2",
            intent="Analogy (Good)",
            keywords=("simulator", "pilot", "training", "practice"),
            response=(
                "Think of it as a flight simulator for investor meetings. You practice "
                "until it feels real."
            ),
            effect="Trust +20, clear framing",
            trust_delta=20,
        ),
        Branch(
            key="3-3",
            intent="Problem solve (Good)",
            keywords=("gen z", "communication", "gap", "text"),
            response=(
                "Gen Z avoids eye contact in interviews. We help teams close that "
                "communication gap fast."
            ),
            effect="Trust +20, problem resonance",
            trust_delta=20,
        ),
        Branch(
            key="3-4",
            intent="Niche (Focused)",
            keywords=("therapy", "autism", "anxiety", "clinical"),
            response="We start with anxiety and autism support. It is a focused DTx wedge.",
            effect="Trust +15, niche focus",
            trust_delta=15,
        ),
        Branch(
            key="3-5",
            intent="Tech heavy (Dry)",
            keywords=("llm", "latency", "model", "vision ai"),
            response="(nods) Tech is fine. What is the business and why now?",
            effect="Trust +5, mild boredom",
            trust_delta=5,
        ),
        Branch(
            key="3-6",
            intent="Comparison (Defensive)",
            keywords=("chatgpt", "zoom", "better", "competition"),
            response=(
                "Differentiation matters. Tell me your edge, not why others are bad."
            ),
            effect="Trust 0, slight pushback",
        ),
        Branch(
            key="3-7",
            intent="Vague (Risky)",
            keywords=("happy", "world", "dream", "vision"),
            response="(smiles) Nice vision, but what is the concrete business model?",
            effect="Trust -10, skepticism",
            trust_delta=-10,
        ),
        Branch(
            key="3-8",
            intent="Overpromise (Worst)",
            keywords=("unicorn", "money", "rich", "billion"),
            response="(frowns) Big claims. Show substance or we are done.",
            effect="Trust -30, trust broken",
            trust_delta=-30,
        ),
    ),
    default_branch="3-7",
)

STAGE_4 = Stage(
    key="STAGE_4",
    title="The Closing",
    prompt="Sarah checks her schedule. Time to wrap up. How do you close the chat?",
    branches=(
        Branch(
            key="4-A",
            intent="QR demo (Best)",
            keywords=("card", "qr", "scan", "instant", "demo"),
            response=(
                "I can email a quick demo link right now. If it looks useful, we can "
                "schedule a follow-up."
            ),
            effect="S Rank",
            final_rank="S",
        ),
        Branch(
            key="4-B",
            intent="Contact request (Normal)",
            keywords=("email", "contact", "later", "send"),
            response="I will email you the deck and a one-pager. Thanks for the time.",
            effect="B Rank",
            final_rank="B",
        ),
        Branch(
            key="4-C",
            intent="Goodbye (Bad)",
            keywords=("bye", "thanks", "go", "see you"),
            response="All right, thanks. See you around.",
            effect="F Rank",
            ends_conversation=True,
            final_rank="F",
        ),
    ),
    default_branch="4-B",
)

STANDUP = StandupScenario(
    key="standup",
    title="Startup Standup 2.0: The Bottleneck Breaker",
    description="You meet Sarah in the SusHi Tech Tokyo 2026 startup lounge.",
    background="Background: SusHi Tech Tokyo 2026 startup lounge",
    npc_state="NPC: Sarah (VC) - state: busy high, guarded high",
    items="Items: candy, QR business card",
    success_message="Nice. I am interested. Let's follow up in a proper meeting.",
    fail_message=(
        "Sorry, I have to run. If there is another chance, we can talk again."
    ),
    stages=(STAGE_1, STAGE_2, STAGE_3, STAGE_4),
)


def get_scenario() -> StandupScenario:
    return STANDUP
