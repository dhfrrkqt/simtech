# Answer Key: Scenario Branch Outputs

아래는 `curator_agent/scenarios.py` 기준으로 각 시나리오 분기점에서
출력되어야 하는 Sarah의 응답(정답) 목록입니다. 입력은 키워드 포함 여부로
매칭되며(대소문자 무시), 각 Stage의 기본 분기(default_branch)도 함께
기록했습니다.

## 공통 출력 규칙

- 매 Stage 입력 후에는 `Sarah: {branch.response}`가 출력됩니다.
- `ends_conversation=True`인 분기에서는 이어서
  `Sarah: The conversation has ended.`가 출력됩니다.
- Stage 1은 Recovery가 있으며, Recovery 키워드에 매칭되면 추가로
  `Sarah: {recovery.response}`가 출력됩니다.
- Stage 4에서 종료되면 마지막에 성공 메시지가 출력됩니다:
  `Sarah: Nice. I am interested. Let's follow up in a proper meeting.`
- 시간 초과 시 실패 메시지가 출력됩니다:
  `Sarah: Sorry, I have to run. If there is another chance, we can talk again.`

## STAGE_1: The Approach (default_branch = 1-B)

1-A (Empathy)
- 키워드: battlefield, war zone, shelter, quiet, hectic
- 사용자 발화 예시:
  - "It's a real war zone in here."
  - "This place feels hectic."
- 출력:
  `Sarah: (smiles) Yeah, it is a war zone. Sure, take a seat. We are all in the trenches today.`

1-B (Simple question)
- 키워드: seat, taken, empty, sit, here
- 사용자 발화 예시:
  - "Is this seat taken?"
  - "Can I sit here?"
- 출력:
  `Sarah: (sigh) It is free. Go ahead. Just keeping up is a lot.`

1-C (Pushy, ends)
- 키워드: move, my seat, sit down, save it
- 사용자 발화 예시:
  - "Move, this is my seat."
  - "I'm sitting down, save it."
- 출력:
  `Sarah: (frowns) Hey. Who do you think you are? Let's reset.`
  `Sarah: The conversation has ended.`

Recovery (trigger: 1-B, 1-C)
- Recovery 키워드: understood, sorry, my bad, apologies, back off, retreat
- 사용자 발화 예시:
  - "Sorry about that. My bad."
  - "I will back off. Apologies."
- 출력:
  `Sarah: Okay. (sigh) If you give me 10 minutes, I can talk later. Sorry, long day.`
- Recovery에 매칭되지 않고 1-C였다면:
  `Sarah: The conversation has ended.`

## STAGE_2: Ice Breaking (default_branch = 2-3)

2-1 (Gift)
- 키워드: candy, sweet, sugar, gift, snack
- 사용자 발화 예시:
  - "I brought a candy as a small gift."
  - "Want a sweet snack?"
- 출력:
  `Sarah: (laughs) You brought candy? That is unexpectedly kind. Nice icebreaker.`

2-2 (Observation)
- 키워드: coffee, caffeine, cup, espresso
- 사용자 발화 예시:
  - "That's your fourth coffee, right?"
  - "Lots of caffeine today?"
- 출력:
  `Sarah: (glances at cup) Fourth cup already. You are really powering through.`

2-3 (Empathy)
- 키워드: crowd, noise, busy, energy
- 사용자 발화 예시:
  - "This crowd is loud and busy."
  - "So much energy here."
- 출력:
  `Sarah: This place is loud. Hard to hear anything, right? Thanks for braving it.`

2-5 (Compliment)
- 키워드: style, sharp, professional, look
- 사용자 발화 예시:
  - "Your style looks sharp today."
  - "You look very professional."
- 출력:
  `Sarah: (smiles) Thanks. Flattery noted. I am just trying to survive the day.`

2-6 (Weather)
- 키워드: weather, snow, cold, finland
- 사용자 발화 예시:
  - "The weather is so cold in Finland."
  - "Snowy day, huh?"
- 출력:
  `Sarah: (dry) Yeah, it is cold. So, what are you here for?`

2-7 (Insult)
- 키워드: old, tired, exhausted
- 사용자 발화 예시:
  - "You look tired."
  - "Are you exhausted?"
- 출력:
  `Sarah: (flat) Excuse me? That is a bit personal. Let's keep it professional.`

2-8 (Hard pitch, ends)
- 키워드: pitch, listen, idea, startup
- 사용자 발화 예시:
  - "Listen to my startup pitch."
  - "I have an idea you need to hear."
- 출력:
  `Sarah: (cuts in) I have ten seconds. Go.`
  `Sarah: The conversation has ended.`

## STAGE_3: The Pitch (default_branch = 3-7)

3-1 (Insight)
- 키워드: psychology, non-verbal, eye contact, behavior
- 사용자 발화 예시:
  - "We focus on psychology and non-verbal behavior."
  - "Eye contact signals are our core."
- 출력:
  `Sarah: We build AI that coaches founders on nonverbal signals in investor conversations. It catches what people miss.`

3-2 (Analogy)
- 키워드: simulator, pilot, training, practice
- 사용자 발화 예시:
  - "It's like a flight simulator for investor meetings."
  - "We train founders the way pilots practice."
- 출력:
  `Sarah: Think of it as a flight simulator for investor meetings. You practice until it feels real.`

3-3 (Problem solve)
- 키워드: gen z, communication, gap, text
- 사용자 발화 예시:
  - "Gen Z has a communication gap in interviews."
  - "We fix the gap caused by texting culture."
- 출력:
  `Sarah: Gen Z avoids eye contact in interviews. We help teams close that communication gap fast.`

3-4 (Niche)
- 키워드: therapy, autism, anxiety, clinical
- 사용자 발화 예시:
  - "We start in therapy, autism, and anxiety support."
  - "Clinical focus first, then expand."
- 출력:
  `Sarah: We start with anxiety and autism support. It is a focused DTx wedge.`

3-5 (Tech heavy)
- 키워드: llm, latency, model, vision ai
- 사용자 발화 예시:
  - "Our LLM and vision AI stack is low latency."
  - "The model latency is our edge."
- 출력:
  `Sarah: (nods) Tech is fine. What is the business and why now?`

3-6 (Comparison)
- 키워드: chatgpt, zoom, better, competition
- 사용자 발화 예시:
  - "We are better than ChatGPT and Zoom."
  - "The competition is weak."
- 출력:
  `Sarah: Differentiation matters. Tell me your edge, not why others are bad.`

3-7 (Vague)
- 키워드: happy, world, dream, vision
- 사용자 발화 예시:
  - "We want to make the world happy."
  - "Our dream and vision are big."
- 출력:
  `Sarah: (smiles) Nice vision, but what is the concrete business model?`

3-8 (Overpromise)
- 키워드: unicorn, money, rich, billion
- 사용자 발화 예시:
  - "We will be a unicorn and make billions."
  - "This will make everyone rich."
- 출력:
  `Sarah: (frowns) Big claims. Show substance or we are done.`

## STAGE_4: The Closing (default_branch = 4-B)

4-A (QR demo)
- 키워드: card, qr, scan, instant, demo
- 사용자 발화 예시:
  - "Scan this QR for an instant demo."
  - "I can send a demo link right now."
- 출력:
  `Sarah: I can email a quick demo link right now. If it looks useful, we can schedule a follow-up.`
- 최종 등급: S

4-B (Contact request)
- 키워드: email, contact, later, send
- 사용자 발화 예시:
  - "I will email you the deck later."
  - "Can I send you the one-pager?"
- 출력:
  `Sarah: I will email you the deck and a one-pager. Thanks for the time.`
- 최종 등급: B

4-C (Goodbye, ends)
- 키워드: bye, thanks, go, see you
- 사용자 발화 예시:
  - "Thanks, I have to go. Bye."
  - "See you around."
- 출력:
  `Sarah: All right, thanks. See you around.`
  `Sarah: The conversation has ended.`
- 최종 등급: F
