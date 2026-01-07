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

const state = {
  mode: "chat",
  active: false,
  recording: false,
  sessionId: null,
  stage: null,
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

const startSession = async () => {
  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
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
};

const speakText = (text) => {
  if (!state.settings.ttsEnabled) return;
  if (!window.speechSynthesis) return;
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
    if (payload.sarah) {
      addBubble(payload.sarah, "agent");
      speakText(payload.sarah);
    }
    if (payload.system) {
      addBubble(payload.system, "coach");
    }
    if (payload.coach_prompt) {
      addBubble(payload.coach_prompt, "coach");
    }
    if (payload.success_message) {
      addBubble(payload.success_message, "agent");
      speakText(payload.success_message);
    }
    if (payload.evaluation) {
      addBubble(payload.evaluation, "coach");
    }
    if (payload.score) {
      scoreValue.textContent = payload.score;
    }
    if (payload.final_rank) {
      scoreNote.textContent = `Final rank: ${payload.final_rank}`;
    }
    if (payload.stage) {
      state.stage = payload.stage;
      updateStageView();
      if (!payload.completed && !payload.coach_prompt) {
        addBubble(`Coach: ${payload.stage.prompt}`, "coach");
      }
    }
    if (payload.completed) {
      setStatus("Complete");
    }
  } catch (error) {
    addBubble("Failed to reach server.", "agent");
  }
};

const mergeBuffers = (buffers, length) => {
  const result = new Float32Array(length);
  let offset = 0;
  buffers.forEach((buffer) => {
    result.set(buffer, offset);
    offset += buffer.length;
  });
  return result;
};

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

const arrayBufferToBase64 = (buffer) => {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
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
  let recordingLength = 0;

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(input));
    recordingLength += input.length;
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  await new Promise((resolve) => setTimeout(resolve, durationMs));

  processor.disconnect();
  source.disconnect();
  stream.getTracks().forEach((track) => track.stop());

  const merged = mergeBuffers(chunks, recordingLength);
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
  if (payload.error) {
    throw new Error(payload.error);
  }
  return payload.transcript || "";
};

sendBtn.addEventListener("click", () => {
  const text = chatInput.value.trim();
  handleSend(text);
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendBtn.click();
  }
});

startBtn.addEventListener("click", () => {
  scenarioModal.classList.add("is-active");
});

closeModal.addEventListener("click", () => {
  scenarioModal.classList.remove("is-active");
});

window.addEventListener("click", (event) => {
  if (event.target === scenarioModal) {
    scenarioModal.classList.remove("is-active");
  }
});

selectScenarioBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const scenario = btn.dataset.scenario;
    if (scenario === "business") {
      scenarioModal.classList.remove("is-active");
      setStatus("Loading");
      startSession();
    }
  });
});

resetBtn.addEventListener("click", resetSession);

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

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    updateModeView();
    saveSettings();
  });
});

scenarioCards.forEach((card) => {
  card.addEventListener("click", () => {
    scenarioCards.forEach((item) => item.classList.remove("is-active"));
    card.classList.add("is-active");
  });
});

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

inputModeRadios.forEach((radio) => {
  radio.addEventListener("change", () => {
    if (!radio.checked) return;
    state.mode = radio.value;
    updateModeView();
    saveSettings();
  });
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
