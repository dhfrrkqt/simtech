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

const scenarioModal = document.getElementById("scenarioModal");
const closeModal = document.getElementById("closeModal");
const selectScenarioBtns = document.querySelectorAll(".select-scenario-btn");

const apiModal = document.getElementById("apiModal");
const closeApiModal = document.getElementById("closeApiModal");
const selectApiBtns = document.querySelectorAll(".select-api-btn");

const state = {
  mode: "chat",
  active: false,
  recording: false,
  sessionId: null,
  stage: null,
  selectedScenario: null,
  selectedApi: null,
  settings: {
    timeout: 240,
    recordSeconds: 5,
    ttsEnabled: false,
  },
};

const addBubble = (text, who) => {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${who}`;
  bubble.textContent = text;
  chatBody.appendChild(bubble);
  chatBody.scrollTop = chatBody.scrollHeight;
  return bubble;
};

const updateStageView = () => {
  if (!state.stage) return;
  stageLabel.textContent = `${state.stage.title} - ${state.stage.prompt}`;
  promptText.textContent = state.stage.prompt;
  stageCount.textContent = `${state.stage.index} / ${state.stage.total}`;
};

const updateModeView = () => {
  modeLabel.textContent = state.mode === "voice" ? "Voice" : "Chat";
  voicePanel.classList.toggle("is-visible", state.mode === "voice");
  chatInputRow.classList.toggle("is-hidden", state.mode === "voice");
  chatInput.placeholder = "Type your response";
  modeButtons.forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.mode === state.mode);
  });
  envMode.textContent = state.mode === "voice" ? "Voice" : "Chat";
  inputModeRadios.forEach((radio) => {
    radio.checked = radio.value === state.mode;
  });
};

const setStatus = (value) => {
  sessionStatus.textContent = value;
};

const updateEnvPanel = () => {
  envTimeout.textContent = `${state.settings.timeout}s`;
  envTts.textContent = state.settings.ttsEnabled ? "On" : "Off";
  envMode.textContent = state.mode === "voice" ? "Voice" : "Chat";
  envRecord.textContent = `${state.settings.recordSeconds}s`;
};

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

const saveSettings = () => {
  localStorage.setItem("uiTimeout", String(state.settings.timeout));
  localStorage.setItem("uiRecordSeconds", String(state.settings.recordSeconds));
  localStorage.setItem("uiTtsEnabled", String(state.settings.ttsEnabled));
  localStorage.setItem("uiInputMode", state.mode);
};

const applyConfigDefaults = async () => {
  if (localStorage.getItem("uiRecordSeconds")) return;
  try {
    const response = await fetch("/api/config");
    const payload = await response.json();
    const recordDefault = Number(payload.record_seconds_default);
    if (recordDefault) {
      state.settings.recordSeconds = recordDefault;
      recordSecondsInput.value = recordDefault;
      updateEnvPanel();
    }
  } catch (error) { }
};

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
    addBubble("Failed to start session.", "agent");
    setStatus("Idle");
  }
};

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
  chatInput.disabled = false;
  sendBtn.disabled = false;
  voiceBtn.disabled = false;
  voiceBtn.textContent = "Record 5s";
};

const speakText = (text) => {
  if (!state.settings.ttsEnabled || !window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.speak(utterance);
};

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
    if (payload.sarah && !payload.completed) {
      addBubble(payload.sarah, "agent");
      speakText(payload.sarah);
    }
    if (payload.system && !payload.completed) addBubble(payload.system, "coach");
    if (payload.coach_prompt && !payload.completed) addBubble(payload.coach_prompt, "coach");

    if (payload.stage) {
      state.stage = payload.stage;
      updateStageView();
      if (!payload.completed && !payload.coach_prompt) {
        addBubble(`Coach: ${payload.stage.prompt}`, "coach");
      }
    }
    if (payload.completed) {
      setStatus("Complete");
      chatInput.disabled = true;
      sendBtn.disabled = true;
      voiceBtn.disabled = true;
      voiceBtn.textContent = "Session Ended";

      // 사이드바 업데이트
      if (payload.score) scoreValue.textContent = payload.score;
      if (payload.final_rank) scoreNote.textContent = `Final rank: ${payload.final_rank}`;

      // 1. 사라의 마지막 대사 (coach 말풍선)
      if (payload.sarah) {
        addBubble(payload.sarah, "coach");
        speakText(payload.sarah);
      }

      // 2. AI 평가 결과 (coach 말풍선)
      if (payload.evaluation) {
        addBubble(payload.evaluation, "coach");
      } else {
        addBubble(`The conversation has ended. Your final score is ${payload.score || "--"}.`, "coach");
      }
    }
  } catch (error) {
    addBubble("Failed to reach server.", "agent");
  }
};

const mergeBuffers = (buffers, length) => {
  const result = new Float32Array(length);
  let offset = 0;
  buffers.forEach((b) => {
    result.set(b, offset);
    offset += b.length;
  });
  return result;
};

const downsampleBuffer = (buffer, sampleRate, targetRate) => {
  if (targetRate === sampleRate) return buffer;
  const ratio = sampleRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = accum / count;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
};

const encodeWav = (samples, sampleRate) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
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
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return buffer;
};

const arrayBufferToBase64 = (buffer) => {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

const recordAudio = async (durationMs = 5000, targetRate = 16000) => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  let length = 0;
  processor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(input));
    length += input.length;
  };
  source.connect(processor);
  processor.connect(audioContext.destination);
  await new Promise((r) => setTimeout(r, durationMs));
  processor.disconnect();
  source.disconnect();
  stream.getTracks().forEach((t) => t.stop());
  const merged = mergeBuffers(chunks, length);
  const downsampled = downsampleBuffer(merged, audioContext.sampleRate, targetRate);
  audioContext.close();
  return encodeWav(downsampled, targetRate);
};

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
  if (payload.error) throw new Error(payload.error);
  return payload.transcript || "";
};

sendBtn.addEventListener("click", () => {
  handleSend(chatInput.value.trim());
});

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

startBtn.addEventListener("click", () => {
  scenarioModal.classList.add("is-active");
});

closeModal.addEventListener("click", () => {
  scenarioModal.classList.remove("is-active");
});

selectScenarioBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const scenario = btn.dataset.scenario;
    if (scenario === "business") {
      state.selectedScenario = scenario;
      scenarioModal.classList.remove("is-active");
      apiModal.classList.add("is-active");
    }
  });
});

closeApiModal.addEventListener("click", () => {
  apiModal.classList.remove("is-active");
});

selectApiBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    state.selectedApi = btn.dataset.api;
    apiModal.classList.remove("is-active");
    setStatus("Loading");
    startSession();
  });
});

window.addEventListener("click", (e) => {
  if (e.target === scenarioModal) scenarioModal.classList.remove("is-active");
  if (e.target === apiModal) apiModal.classList.remove("is-active");
});

resetBtn.addEventListener("click", resetSession);

voiceBtn.addEventListener("click", () => {
  if (state.recording) return;
  if (!navigator.mediaDevices?.getUserMedia) return;
  const recordSeconds = Math.max(2, state.settings.recordSeconds);
  state.recording = true;
  voiceBtn.textContent = "Recording...";
  recordAudio(recordSeconds * 1000, 16000)
    .then((wav) => requestServerStt(wav))
    .then((t) => {
      if (!t) return;
      handleSend(t);
    })
    .finally(() => {
      state.recording = false;
      voiceBtn.textContent = "Record 5s";
    });
});

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    updateModeView();
    saveSettings();
  });
});

scenarioCards.forEach((card) => {
  card.addEventListener("click", () => {
    scenarioCards.forEach((i) => i.classList.remove("is-active"));
    card.classList.add("is-active");
  });
});

settingsForm.addEventListener("submit", (e) => {
  e.preventDefault();
  state.settings.timeout = Number(timeoutInput.value) || 240;
  state.settings.recordSeconds = Number(recordSecondsInput.value) || 5;
  state.settings.ttsEnabled = ttsToggle.checked;
  state.mode = [...inputModeRadios].find((r) => r.checked)?.value || "chat";
  updateEnvPanel();
  updateModeView();
  saveSettings();
});

ttsToggle.addEventListener("change", () => {
  state.settings.ttsEnabled = ttsToggle.checked;
  updateEnvPanel();
  saveSettings();
});

loadSettings();
updateStageView();
resetSession();
applyConfigDefaults();
