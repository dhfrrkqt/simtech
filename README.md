# Test Agents

## 설치 (uv)

1) 가상환경 생성:
```bash
uv venv
```

2) 의존성 설치:
```bash
uv pip install -r requirements.txt
```

필요하면 동기화 방식으로 설치:
```bash
uv pip sync -r requirements.txt
```

## 환경 변수

`.env` 파일을 생성하고 아래 내용을 설정하세요:
```bash
GOOGLE_API_KEY=
GOOGLE_GENAI_USE_VERTEXAI=FALSE
USE_GEMINI=true
FALLBACK_TO_LOCAL=true
OLLAMA_HOST=host.docker.internal
TTS_ENABLED=FALSE
SCENARIO_TIME_LIMIT_SECONDS=240
SCENARIO_INPUT_MODE=chat
SCENARIO_VOICE_LANGUAGE=en-US
SCENARIO_VOICE_SAMPLE_RATE=16000
SCENARIO_VOICE_RECORD_SECONDS=5
SCENARIO_VOICE_AUDIO_PATH=
UI_RECORD_SECONDS=5
```

## TTS (Linux/WSL)

`pyttsx3` 사용을 위해 시스템 패키지가 필요합니다:
```bash
sudo apt update
sudo apt install espeak-ng
```

`aplay` 오류가 나면:
```bash
sudo apt update
sudo apt install alsa-utils
```

TTS를 사용하려면 `.env`에서 다음을 설정하세요:
```bash
TTS_ENABLED=true
```

## 실행

시나리오 실행:
```bash
python main.py
```

## UI 실행

UI 서버 실행:
```bash
python ui_server.py
```

브라우저에서 접속:
```bash
http://localhost:8000
```
