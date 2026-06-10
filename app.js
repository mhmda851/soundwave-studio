"use strict";

const NUM_COLUMNS = 48;
const BLOCK_GAP = 2;
const COLUMN_GAP = 3;
const RISE_SPEED = 0.35;
const FALL_SPEED = 0.08;
const GAIN_STEP = 0.15;
const GAIN_MIN = 0.1;
const GAIN_MAX = 6.0;

const COLOR_BOTTOM = [50, 220, 80];
const COLOR_MIDDLE = [255, 220, 50];
const COLOR_TOP = [220, 50, 255];

const state = {
  activeTab: "visualizer",
  viewMode: "blocks",
  gain: 1.0,
  levels: new Float32Array(NUM_COLUMNS),
  meterLevel: 0,
  meterPeak: 0,
  audioReady: false,
  isRecording: false,
  recordStart: 0,
  recordTimerId: null,
  mediaRecorder: null,
  recordedChunks: [],
  lastBlobUrl: null,
  deferredInstall: null,
};

let audioContext = null;
let analyser = null;
let mediaStream = null;
let animationId = null;
let freqData = null;
let timeData = null;

const canvas = document.getElementById("viz-canvas");
const ctx = canvas.getContext("2d");
const statusText = document.getElementById("status-text");
const gainLabel = document.getElementById("gain-label");
const meterFill = document.getElementById("meter-fill");
const meterPeak = document.getElementById("meter-peak");
const meterValue = document.getElementById("meter-value");
const recIndicator = document.getElementById("rec-indicator");
const recTimer = document.getElementById("rec-timer");
const recStatus = document.getElementById("rec-status");
const downloadLink = document.getElementById("download-link");
const btnStart = document.getElementById("btn-start");
const btnInstall = document.getElementById("btn-install");
const btnRecord = document.getElementById("btn-record");
const btnViewMode = document.getElementById("btn-view-mode");

function lerpColor(ratio) {
  const r = Math.max(0, Math.min(1, ratio));
  let c;
  if (r <= 0.5) {
    const t = r / 0.5;
    c = COLOR_BOTTOM.map((v, i) => v * (1 - t) + COLOR_MIDDLE[i] * t);
  } else {
    const t = (r - 0.5) / 0.5;
    c = COLOR_MIDDLE.map((v, i) => v * (1 - t) + COLOR_TOP[i] * t);
  }
  return `rgb(${c.map((v) => Math.round(v)).join(",")})`;
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function setStatus(msg) {
  statusText.textContent = msg;
}

function resizeCanvas() {
  const wrap = canvas.parentElement;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function buildBandMap(fftSize, sampleRate) {
  const nyquist = sampleRate / 2;
  const binCount = fftSize / 2;
  const edges = [];
  const minF = 20;
  for (let i = 0; i <= NUM_COLUMNS; i++) {
    const t = i / NUM_COLUMNS;
    edges.push(minF * Math.pow(nyquist / minF, t));
  }

  const map = [];
  for (let band = 0; band < NUM_COLUMNS; band++) {
    const low = edges[band];
    const high = edges[band + 1];
    const bins = [];
    for (let b = 0; b < binCount; b++) {
      const freq = (b * sampleRate) / fftSize;
      if (freq >= low && freq < high) bins.push(b);
    }
    map.push(bins);
  }
  return map;
}

let bandMap = [];

function processAudio() {
  if (!analyser || !freqData) return;

  analyser.getByteFrequencyData(freqData);
  const targets = new Float32Array(NUM_COLUMNS);

  for (let i = 0; i < NUM_COLUMNS; i++) {
    const bins = bandMap[i];
    if (!bins.length) continue;
    let sum = 0;
    for (const b of bins) sum += freqData[b];
    const avg = (sum / bins.length / 255) * state.gain;
    targets[i] = Math.min(0.65, Math.pow(Math.log1p(avg * 8), 0.75) * 0.65);
  }

  const maxT = Math.max(...targets, 0.001);
  for (let i = 0; i < NUM_COLUMNS; i++) {
    const t = targets[i] / maxT * 0.65;
    if (t > state.levels[i]) {
      state.levels[i] += (t - state.levels[i]) * RISE_SPEED;
    } else {
      state.levels[i] += (t - state.levels[i]) * FALL_SPEED;
    }
  }

  analyser.getByteTimeDomainData(timeData);
  let sumSq = 0;
  for (let i = 0; i < timeData.length; i++) {
    const v = (timeData[i] - 128) / 128;
    sumSq += v * v;
  }
  const rms = Math.sqrt(sumSq / timeData.length) * state.gain;
  const meterTarget = Math.min(1, rms / 0.22);
  if (meterTarget > state.meterLevel) {
    state.meterLevel += (meterTarget - state.meterLevel) * RISE_SPEED;
  } else {
    state.meterLevel += (meterTarget - state.meterLevel) * FALL_SPEED;
  }
  if (state.meterLevel >= state.meterPeak) {
    state.meterPeak = state.meterLevel;
  } else {
    state.meterPeak = Math.max(state.meterLevel, state.meterPeak - 0.012);
  }

  meterFill.style.height = `${state.meterLevel * 100}%`;
  meterPeak.style.bottom = `${state.meterPeak * 100}%`;
  meterPeak.style.opacity = state.meterPeak > 0.02 ? "1" : "0";
  meterValue.textContent = String(Math.round(state.meterLevel * 100));
}

function drawBlocks(w, h) {
  const margin = 12;
  const meterSpace = 44;
  const availW = w - margin * 2 - meterSpace;
  const availH = h - margin * 2;
  const blockSize = Math.max(4, Math.floor((availW - (NUM_COLUMNS - 1) * COLUMN_GAP) / NUM_COLUMNS));
  const rowGap = Math.max(1, Math.floor(blockSize / 5));
  const maxBlocks = Math.max(1, Math.floor(availH / (blockSize + rowGap)));
  const gridW = NUM_COLUMNS * blockSize + (NUM_COLUMNS - 1) * COLUMN_GAP;
  const gridH = maxBlocks * blockSize + (maxBlocks - 1) * rowGap;
  const ox = margin + meterSpace + Math.max(0, (availW - gridW) / 2);
  const oy = margin + Math.max(0, (availH - gridH) / 2);

  for (let col = 0; col < NUM_COLUMNS; col++) {
    const active = Math.floor(state.levels[col] * maxBlocks);
    const x = ox + col * (blockSize + COLUMN_GAP);
    for (let row = 0; row < maxBlocks; row++) {
      const blockIndex = maxBlocks - 1 - row;
      const y = oy + row * (blockSize + rowGap);
      if (blockIndex < active) {
        ctx.fillStyle = lerpColor(blockIndex / Math.max(1, maxBlocks - 1));
      } else {
        ctx.fillStyle = "#0f0f0f";
      }
      ctx.fillRect(x, y, blockSize, blockSize);
    }
  }
}

function drawWaves(w, h) {
  const margin = 12;
  const meterSpace = 44;
  const availW = w - margin * 2 - meterSpace;
  const availH = h - margin * 2;
  const ox = margin + meterSpace;
  const oy = margin;
  const centerY = oy + availH / 2;
  const amplitude = availH / 2;

  const step = availW / (NUM_COLUMNS - 1);
  const points = [];
  for (let i = 0; i < NUM_COLUMNS; i++) {
    points.push({
      x: ox + i * step,
      y: centerY - state.levels[i] * amplitude,
    });
  }

  ctx.strokeStyle = "#191919";
  ctx.beginPath();
  ctx.moveTo(ox, centerY);
  ctx.lineTo(ox + availW, centerY);
  ctx.stroke();

  const smoothCount = Math.max(120, Math.floor(availW * 0.8));
  const smoothX = [];
  const smoothY = [];
  for (let i = 0; i < smoothCount; i++) {
    const t = (i / (smoothCount - 1)) * (NUM_COLUMNS - 1);
    const idx = Math.floor(t);
    const frac = t - idx;
    const i0 = Math.min(idx, NUM_COLUMNS - 1);
    const i1 = Math.min(idx + 1, NUM_COLUMNS - 1);
    const y = points[i0].y * (1 - frac) + points[i1].y * frac;
    smoothX.push(ox + (i / (smoothCount - 1)) * availW);
    smoothY.push(y);
  }

  for (let i = 0; i < smoothCount - 1; i++) {
    const x0 = smoothX[i];
    const x1 = smoothX[i + 1];
    const y0u = smoothY[i];
    const y1u = smoothY[i + 1];
    const y0l = centerY + (centerY - y0u);
    const y1l = centerY + (centerY - y1u);
    const ratio = Math.min(1, Math.max(0, (centerY - (y0u + y1u) / 2) / amplitude));
    ctx.fillStyle = lerpColor(ratio);
    ctx.beginPath();
    ctx.moveTo(x0, y0u);
    ctx.lineTo(x1, y1u);
    ctx.lineTo(x1, y1l);
    ctx.lineTo(x0, y0l);
    ctx.closePath();
    ctx.fill();
  }

  ctx.strokeStyle = "rgba(255,255,255,0.7)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  smoothX.forEach((x, i) => (i === 0 ? ctx.moveTo(x, smoothY[i]) : ctx.lineTo(x, smoothY[i])));
  ctx.stroke();
}

function drawFrame() {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, w, h);

  if (state.audioReady) {
    processAudio();
    if (state.viewMode === "blocks") drawBlocks(w, h);
    else drawWaves(w, h);
  } else {
    ctx.fillStyle = "#555";
    ctx.font = "16px system-ui";
    ctx.textAlign = "center";
    ctx.fillText("اضغط «ابدأ الميكروفون» بالأسفل", w / 2, h / 2);
  }

  animationId = requestAnimationFrame(drawFrame);
}

async function startAudio() {
  if (state.audioReady) return;

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: false,
      },
      video: false,
    });

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(mediaStream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.75;
    source.connect(analyser);
    freqData = new Uint8Array(analyser.frequencyBinCount);
    timeData = new Uint8Array(analyser.fftSize);
    bandMap = buildBandMap(analyser.fftSize, audioContext.sampleRate);

    state.audioReady = true;
    btnStart.classList.add("hidden");
    btnRecord.disabled = false;
    setStatus("الميكروفون نشط — قناة واحدة للمحلل والمسجّل");
  } catch (err) {
    setStatus(`تعذّر الوصول للميكروفون: ${err.message}`);
  }
}

function getRecorderMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) || "";
}

function startRecording() {
  if (!mediaStream || state.isRecording) return;

  state.recordedChunks = [];
  const mimeType = getRecorderMimeType();
  const options = mimeType ? { mimeType } : undefined;

  try {
    state.mediaRecorder = new MediaRecorder(mediaStream, options);
  } catch (err) {
    setStatus(`فشل بدء التسجيل: ${err.message}`);
    return;
  }

  state.mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) state.recordedChunks.push(e.data);
  };

  state.mediaRecorder.onstop = () => {
    const type = state.mediaRecorder.mimeType || "audio/webm";
    const blob = new Blob(state.recordedChunks, { type });
    if (state.lastBlobUrl) URL.revokeObjectURL(state.lastBlobUrl);
    state.lastBlobUrl = URL.createObjectURL(blob);
    const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
    const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    downloadLink.href = state.lastBlobUrl;
    downloadLink.download = `recording_${stamp}.${ext}`;
    downloadLink.classList.remove("hidden");
    downloadLink.textContent = `تنزيل ${downloadLink.download}`;
    recStatus.textContent = "تم الحفظ — اضغط التنزيل";
    setStatus(`تم حفظ التسجيل (${downloadLink.download})`);
  };

  state.mediaRecorder.start(250);
  state.isRecording = true;
  state.recordStart = Date.now();
  btnRecord.classList.add("recording");
  btnRecord.textContent = "■";
  recIndicator.classList.remove("hidden");
  recStatus.textContent = "جاري التسجيل...";

  state.recordTimerId = setInterval(() => {
    recTimer.textContent = formatDuration((Date.now() - state.recordStart) / 1000);
  }, 200);
}

function stopRecording() {
  if (!state.isRecording || !state.mediaRecorder) return;
  state.mediaRecorder.stop();
  state.isRecording = false;
  btnRecord.classList.remove("recording");
  btnRecord.textContent = "●";
  recIndicator.classList.add("hidden");
  clearInterval(state.recordTimerId);
  recStatus.textContent = "جاهز للتسجيل";
}

function toggleRecording() {
  if (!state.audioReady) return;
  if (state.isRecording) stopRecording();
  else startRecording();
}

function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".tab").forEach((el) => {
    const active = el.dataset.tab === tab;
    el.classList.toggle("active", active);
    el.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.querySelectorAll(".panel").forEach((el) => {
    const active = el.id === `panel-${tab}`;
    el.classList.toggle("active", active);
    el.hidden = !active;
  });
  if (tab === "visualizer") requestAnimationFrame(resizeCanvas);
}

function getBasePath() {
  const parts = location.pathname.split("/").filter(Boolean);
  if (parts.length > 0 && parts[0] !== "index.html") {
    return `/${parts[0]}/`;
  }
  return "./";
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    const base = getBasePath();
    navigator.serviceWorker.register(`${base}sw.js`, { scope: base }).catch(() => {});
  }
}

function setupInstallPrompt() {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    state.deferredInstall = e;
    btnInstall.classList.remove("hidden");
  });

  btnInstall.addEventListener("click", async () => {
    if (!state.deferredInstall) return;
    state.deferredInstall.prompt();
    await state.deferredInstall.userChoice;
    state.deferredInstall = null;
    btnInstall.classList.add("hidden");
  });
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

btnStart.addEventListener("click", startAudio);
btnRecord.addEventListener("click", toggleRecording);
btnViewMode.addEventListener("click", () => {
  state.viewMode = state.viewMode === "blocks" ? "waves" : "blocks";
  btnViewMode.textContent = state.viewMode === "blocks" ? "موجات" : "أعمدة";
});
document.getElementById("btn-gain-up").addEventListener("click", () => {
  state.gain = Math.min(GAIN_MAX, state.gain + GAIN_STEP);
  gainLabel.textContent = `حساسية ${state.gain.toFixed(1)}`;
});
document.getElementById("btn-gain-down").addEventListener("click", () => {
  state.gain = Math.max(GAIN_MIN, state.gain - GAIN_STEP);
  gainLabel.textContent = `حساسية ${state.gain.toFixed(1)}`;
});

window.addEventListener("resize", resizeCanvas);
window.addEventListener("orientationchange", () => setTimeout(resizeCanvas, 200));

registerServiceWorker();
setupInstallPrompt();
resizeCanvas();
drawFrame();
