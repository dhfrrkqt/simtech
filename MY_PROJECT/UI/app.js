/**
 * UI 요소 및 전역 상태 관리
 */
const chatBody = document.getElementById("chatBody");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");
const startBtn = document.getElementById("startBtn");
const stageLabel = document.getElementById("stageLabel");
const promptText = document.getElementById("promptText");
const stageCount = document.getElementById("stageCount");
const modeLabel = document.getElementById("modeLabel");
const sessionStatus = document.getElementById("sessionStatus");
const scoreValue = document.getElementById("scoreValue");
const scoreNote = document.getElementById("scoreNote");
const envTimeout = document.getElementById("envTimeout");
const envTts = document.getElementById("envTts");
const envMode = document.getElementById("envMode");
const envRecord = document.getElementById("envRecord");
const settingsForm = document.getElementById("settingsForm");
const timeoutInput = document.getElementById("timeoutInput");
const recordSecondsInput = document.getElementById("recordSecondsInput");
const ttsToggle = document.getElementById("ttsToggle");
const inputModeRadios = document.querySelectorAll('input[name="inputMode"]');
const voicePanel = document.getElementById("voicePanel");
const chatInputRow = document.getElementById("chatInputRow");
const voiceBtn = document.getElementById("voiceBtn");
const voiceStatus = document.getElementById("voiceStatus");
const modeButtons = document.querySelectorAll("[data-mode]");
const scenarioCards = document.querySelectorAll("[data-scenario]");

/**
 * 시나리오 선택 모달 관련 요소
 */
const scenarioModal = document.getElementById("scenarioModal");
const closeModal = document.getElementById("closeModal");
const selectScenarioBtns = document.querySelectorAll(".select-scenario-btn");

/**
 * API 선택 모달 관련 요소
 */
const apiModal = document.getElementById("apiModal");
const closeApiModal = document.getElementById("closeApiModal");
const selectApiBtns = document.querySelectorAll(".select-api-btn");

/**
 * 애플리케이션의 현재 상태를 저장하는 객체
 */
const state = {
  mode: "chat",         // 입력 모드 (chat 또는 voice)
  active: false,       // 세션 활성화 여부
  recording: false,    // 현재 녹음 중인지 여부
  sessionId: null,     // 현재 세션 고유 ID
  stage: null,         // 현재 진행 중인 시나리오 스테이지 정보
  selectedScenario: null, // 임시 저장된 시나리오 키
  selectedApi: null,      // 선택된 API (gemini 또는 openai)
  settings: {
    timeout: 240,      // 세션 타임아웃 (초)
    recordSeconds: 5,  // 음성 녹음 시간 (초)
    ttsEnabled: false, // TTS(음성 합성) 사용 여부
  },
};

/**
 * 채팅창에 메시지 말풍선을 추가합니다.
 * @param {string} text - 표시할 메시지 텍스트
 * @param {string} who - 메시지 주체 ('user', 'agent', 'coach')
 */
const addBubble = (text, who) => {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${who}`;
  bubble.textContent = text;
  chatBody.appendChild(bubble);
  // 스크롤을 항상 최하단으로 유지
  chatBody.scrollTop = chatBody.scrollHeight;
  return bubble;
};

/**
 * 현재 스테이지 정보를 UI에 업데이트합니다.
 */
const updateStageView = () => {
  if (!state.stage) return;
  stageLabel.textContent = `${state.stage.title} - ${state.stage.prompt}`;
  promptText.textContent = state.stage.prompt;
  stageCount.textContent = `${state.stage.index} / ${state.stage.total}`;
};

/**
 * 현재 입력 모드(채팅/음성)에 따라 UI를 전환합니다.
 */
const updateModeView = () => {
  modeLabel.textContent = state.mode === "voice" ? "Voice" : "Chat";
  voicePanel.classList.toggle("is-visible", state.mode === "voice");
  chatInputRow.classList.toggle("is-hidden", state.mode === "voice");
  chatInput.placeholder = "Type your response";

  // 모드 버튼 활성화 상태 업데이트
  modeButtons.forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.mode === state.mode);
  });

  envMode.textContent = state.mode === "voice" ? "Voice" : "Chat";

  // 설정 폼의 라디오 버튼 동기화
  inputModeRadios.forEach((radio) => {
    radio.checked = radio.value === state.mode;
  });
};

/**
 * 세션의 현재 상태 텍스트를 업데이트합니다.
 */
const setStatus = (value) => {
  sessionStatus.textContent = value;
};

/**
 * 설정값이 변경될 때 환경 패널의 텍스트를 업데이트합니다.
 */
const updateEnvPanel = () => {
  envTimeout.textContent = `${state.settings.timeout}s`;
  envTts.textContent = state.settings.ttsEnabled ? "On" : "Off";
  envMode.textContent = state.mode === "voice" ? "Voice" : "Chat";
  envRecord.textContent = `${state.settings.recordSeconds}s`;
};

/**
 * 로컬 스토리지에서 이전 설정을 로드합니다.
 */
const loadSettings = () => {
  const savedTimeout = Number(localStorage.getItem("uiTimeout")) || 240;
  const savedTts = localStorage.getItem("uiTtsEnabled") === "true";
  const savedMode = localStorage.getItem("uiInputMode") || "chat";
  const savedRecordRaw = localStorage.getItem("uiRecordSeconds");
  const savedRecord = savedRecordRaw ? Number(savedRecordRaw) : 5;

  state.settings.timeout = savedTimeout;
  state.settings.recordSeconds = savedRecord;
  state.settings.ttsEnabled = savedTts;
  state.mode = savedMode;

  timeoutInput.value = savedTimeout;
  recordSecondsInput.value = savedRecord;
  ttsToggle.checked = savedTts;

  inputModeRadios.forEach((radio) => {
    radio.checked = radio.value === savedMode;
  });

  updateEnvPanel();
  updateModeView();
};

/**
 * 현재 설정을 로컬 스토리지에 저장합니다.
 */
const saveSettings = () => {
  localStorage.setItem("uiTimeout", String(state.settings.timeout));
  localStorage.setItem("uiRecordSeconds", String(state.settings.recordSeconds));
  localStorage.setItem("uiTtsEnabled", String(state.settings.ttsEnabled));
  localStorage.setItem("uiInputMode", state.mode);
};

/**
 * 서버로부터 기본 설정값을 가져와 적용합니다.
 */
const applyConfigDefaults = async () => {
  if (localStorage.getItem("uiRecordSeconds")) {
    return;
  }
  try {
    const response = await fetch("/api/config");
    const payload = await response.json();
    const recordDefault = Number(payload.record_seconds_default);
    if (recordDefault) {
      state.settings.recordSeconds = recordDefault;
      recordSecondsInput.value = recordDefault;
      updateEnvPanel();
    }
  } catch (error) {
    return;
  }
};

/**
 * 새로운 세션을 시작하기 위해 서버에 요청을 보냅니다.
 */
const startSession = async () => {
  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_key: state.selectedScenario,
        api_choice: state.selectedApi,
        timeout_seconds: state.settings.timeout,
        tts_enabled: state.settings.ttsEnabled,
        input_mode: state.mode,
      }),
    });
    const payload = await response.json();
    if (payload.error) {
      addBubble(payload.error, "agent");
      setStatus("Idle");
      return;
    }
    state.sessionId = payload.session_id;
    state.stage = payload.stage;
    updateStageView();
    setStatus("Active");
    addBubble(`Coach: ${payload.stage.prompt}`, "coach");
  } catch (error) {
    addBubble("Failed to start session. Is the server running?", "agent");
    setStatus("Idle");
  }
};

/**
 * 현재 세션을 초기화하고 UI를 초기 상태로 되돌립니다.
 */
const resetSession = () => {
  chatBody.innerHTML = "";
  state.active = false;
  state.sessionId = null;
  state.stage = null;
  updateStageView();
  setStatus("Idle");
  addBubble("Session ready. Click Start when you are ready.", "agent");
  scoreValue.textContent = "--";
  scoreNote.textContent = "Score updates after the session ends.";

  // 세션 리셋 시 입력 다시 활성화
  chatInput.disabled = false;
  sendBtn.disabled = false;
  voiceBtn.disabled = false;
  voiceBtn.textContent = "Record 5s";
};

/**
 * 브라우저의 Web Speech API를 사용하여 텍스트를 음성으로 읽어줍니다.
 */
const speakText = (text) => {
  if (!state.settings.ttsEnabled) return;
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.speak(utterance);
};

/**
 * 사용자가 보낸 텍스트 메시지를 서버로 전송하고 응답을 처리합니다.
 */
const handleSend = async (text) => {
  if (!text || !state.sessionId) return;
  if (!state.active) {
    setStatus("Active");
    state.active = true;
  }
  addBubble(text, "user");
  chatInput.value = "";
  try {
    const response = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        text,
      }),
    });
    const payload = await response.json();
    if (payload.error) {
      addBubble(payload.error, "agent");
      return;
    }
    // NPC(사라)의 응답 표시
    if (payload.sarah) {
      addBubble(payload.sarah, "agent");
      speakText(payload.sarah);
    }
    // 시스템 메시지 응답 표시
    if (payload.system) {
      addBubble(payload.system, "coach");
    }
    // 코치(가이드)의 조언 표시
    if (payload.coach_prompt) {
      addBubble(payload.coach_prompt, "coach");
    }
    // 성공 시 특별 메시지 표시
    if (payload.success_message) {
      addBubble(payload.success_message, "agent");
      speakText(payload.success_message);
    }
    // 대화 종료 후 평가 결과 표시
    if (payload.evaluation) {
      addBubble(payload.evaluation, "coach");
    }
    if (payload.score) {
      scoreValue.textContent = payload.score;
    }
    if (payload.final_rank) {
      scoreNote.textContent = `Final rank: ${payload.final_rank}`;
    }
    // 다음 스테이지로 업데이트
    if (payload.stage) {
      state.stage = payload.stage;
      updateStageView();
      if (!payload.completed && !payload.coach_prompt) {
        addBubble(`Coach: ${payload.stage.prompt}`, "coach");
      }
    }
    // 세션 완료 처리
    if (payload.completed) {
      setStatus("Complete");
      // 세션 종료 시 입력 비활성화
      chatInput.disabled = true;
      sendBtn.disabled = true;
      voiceBtn.disabled = true;
      voiceBtn.textContent = "Session Ended";
    }
  } catch (error) {
    addBubble("Failed to reach server.", "agent");
  }
};

/**
 * 오디오 버퍼들을 하나로 합칩니다.
 */
const mergeBuffers = (buffers, length) => {
  const result = new Float32Array(length);
  let offset = 0;
  buffers.forEach((buffer) => {
    result.set(buffer, offset);
    offset += buffer.length;
  });
  return result;
};

/**
 * 오디오 샘플링 속도를 변환합니다 (예: 44.1kHz -> 16kHz).
 */
const downsampleBuffer = (buffer, sampleRate, targetRate) => {
  if (targetRate === sampleRate) {
    return buffer;
  }
  const ratio = sampleRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      accum += buffer[i];
      count += 1;
    }
    result[offsetResult] = accum / count;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
};

/**
 * 부동 소수점 오디오 데이터를 16비트 PCM WAV 형식으로 인코딩합니다.
 */
const encodeWav = (samples, sampleRate) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i += 1) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return buffer;
};

/**
 * ArrayBuffer를 Base64 문자열로 변환합니다.
 */
const arrayBufferToBase64 = (buffer) => {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

/**
 * 마이크로부터 일정 시간 동안 오디오를 녹음합니다.
 */
const recordAudio = async (durationMs = 5000, targetRate = 16000) => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  let recordingLength = 0;

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(input));
    recordingLength += input.length;
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  // 지정된 시간 동안 대기
  await new Promise((resolve) => setTimeout(resolve, durationMs));

  // 녹음 중지 및 리소스 정리
  processor.disconnect();
  source.disconnect();
  stream.getTracks().forEach((track) => track.stop());

  const merged = mergeBuffers(chunks, recordingLength);
  const downsampled = downsampleBuffer(merged, audioContext.sampleRate, targetRate);
  audioContext.close();
  return encodeWav(downsampled, targetRate);
};

/**
 * 서버에 음성 데이터를 보내 텍스트로 변환(STT)합니다.
 */
const requestServerStt = async (wavBuffer) => {
  const audioBase64 = arrayBufferToBase64(wavBuffer);
  const response = await fetch("/api/voice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      audio_base64: audioBase64,
      sample_rate: 16000,
      language_code: "en-US",
    }),
  });
  const payload = await response.json();
  if (payload.error) {
    throw new Error(payload.error);
  }
  return payload.transcript || "";
};

/**
 * 이벤트 리스너 등록
 */

// 전송 버튼 클릭 시 메시지 처리
sendBtn.addEventListener("click", () => {
  const text = chatInput.value.trim();
  handleSend(text);
});

// 입력창에서 엔터 키를 누르면 메시지 전송
chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendBtn.click();
  }
});

// 세션 시작 버튼 클릭 시 시나리오 선택 모달을 띄웁니다.
startBtn.addEventListener("click", () => {
  scenarioModal.classList.add("is-active");
});

// 모달 닫기 버튼 클릭 시 모달을 숨깁니다.
closeModal.addEventListener("click", () => {
  scenarioModal.classList.remove("is-active");
});

// 시나리오 선택 버튼 클릭 시 처리
selectScenarioBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const scenario = btn.dataset.scenario;
    if (scenario === "business") {
      // 시나리오 임시 저장 후 API 선택 모달로 넘어갑니다.
      state.selectedScenario = scenario;
      scenarioModal.classList.remove("is-active");
      apiModal.classList.add("is-active");
    }
  });
});

// API 선택 제어 버튼 이벤트
closeApiModal.addEventListener("click", () => {
  apiModal.classList.remove("is-active");
});

// API 선택 버튼 클릭 시 세션 진짜 시작
selectApiBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    state.selectedApi = btn.dataset.api;
    apiModal.classList.remove("is-active");
    setStatus("Loading");
    startSession();
  });
});

// 모달 외부 영역 클릭 시 닫기 (API 모달 포함)
window.addEventListener("click", (event) => {
  if (event.target === scenarioModal) {
    scenarioModal.classList.remove("is-active");
  }
  if (event.target === apiModal) {
    apiModal.classList.remove("is-active");
  }
});

// 리셋 버튼 클릭
resetBtn.addEventListener("click", resetSession);

// 음성 녹음 버튼 클릭 시 녹음 및 STT 과정 실행
voiceBtn.addEventListener("click", () => {
  if (state.recording) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    voiceStatus.textContent = "Microphone access not available in this browser.";
    return;
  }
  const recordSeconds = Math.max(2, state.settings.recordSeconds);
  const recordMs = recordSeconds * 1000;
  state.recording = true;
  voiceBtn.textContent = "Recording...";
  voiceStatus.textContent = `Recording ${recordSeconds} seconds...`;
  addBubble("Recording...", "coach");

  recordAudio(recordMs, 16000)
    .then((wavBuffer) => requestServerStt(wavBuffer))
    .then((transcript) => {
      if (!transcript) {
        voiceStatus.textContent = "No speech detected. Try again.";
        addBubble("No speech detected.", "coach");
        return;
      }
      voiceStatus.textContent = "Transcribed. Sending...";
      addBubble("Transcribed. Sending response...", "coach");
      handleSend(transcript);
    })
    .catch((error) => {
      voiceStatus.textContent = `Voice error: ${error.message}`;
      addBubble(`Voice error: ${error.message}`, "coach");
    })
    .finally(() => {
      state.recording = false;
      voiceBtn.textContent = "Record 5s";
      if (!voiceStatus.textContent.startsWith("Voice error")) {
        voiceStatus.textContent = "Tap record to speak again.";
      }
    });
});

// 사이드바의 입력 모드 전환 버튼 이벤트
modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    updateModeView();
    saveSettings();
  });
});

// 시나리오 카드 선택 효과
scenarioCards.forEach((card) => {
  card.addEventListener("click", () => {
    scenarioCards.forEach((item) => item.classList.remove("is-active"));
    card.classList.add("is-active");
  });
});

// 설정 폼 제출 시 값 업데이트 및 저장
settingsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const newTimeout = Number(timeoutInput.value) || 240;
  const newRecordSeconds = Number(recordSecondsInput.value) || 5;
  const selectedMode = [...inputModeRadios].find((radio) => radio.checked)?.value;

  state.settings.timeout = newTimeout;
  state.settings.recordSeconds = newRecordSeconds;
  state.settings.ttsEnabled = ttsToggle.checked;
  state.mode = selectedMode || "chat";

  updateEnvPanel();
  updateModeView();
  saveSettings();
});

// 설정 폼 내부의 입력 모드 라디오 버튼 변경 시 동기화
inputModeRadios.forEach((radio) => {
  radio.addEventListener("change", () => {
    if (!radio.checked) return;
    state.mode = radio.value;
    updateModeView();
    saveSettings();
  });
});

// TTS 토글 변경 시 설정 업데이트
ttsToggle.addEventListener("change", () => {
  state.settings.ttsEnabled = ttsToggle.checked;
  updateEnvPanel();
  saveSettings();
});

/**
 * 초기화 및 초기 설정 로드
 */
loadSettings();
updateStageView();
resetSession();
applyConfigDefaults();
