const CONFIG = {
  // Leave blank to run the complete interface with sample results.
  // Set to an HTTPS API origin when the backend is ready, e.g. https://api.pitchcraft.com
  API_BASE_URL: "",
  MAX_FILE_BYTES: 50 * 1024 * 1024,
  POLL_INTERVAL_MS: 1500,
};

const state = {
  file: null,
  jobId: null,
  notes: [],
  duration: 0,
  playing: false,
  startedAt: 0,
  pausedAt: 0,
  animationFrame: null,
  voices: [],
  abortController: null,
};

const $ = (selector) => document.querySelector(selector);
const elements = {
  form: $("#upload-form"), fileInput: $("#audio-file"), dropZone: $("#drop-zone"), selectedFile: $("#selected-file"),
  fileName: $("#file-name"), fileSize: $("#file-size"), removeFile: $("#remove-file"), error: $("#form-error"),
  submit: $("#submit-button"), uploadCard: $("#upload-card"), process: $("#process-panel"), progressBar: $("#progress-bar"),
  progressPercent: $("#progress-percent"), processTitle: $("#process-title"), cancel: $("#cancel-button"), results: $("#results"),
  startOver: $("#start-over"), play: $("#play-button"), timeline: $("#timeline"), currentTime: $("#current-time"),
  totalTime: $("#total-time"), sound: $("#sound-select"), pianoRoll: $("#piano-roll"), noteCount: $("#note-count"),
  durationLabel: $("#duration-label"), rangeLabel: $("#range-label"), resultSummary: $("#result-summary"),
  midiDownload: $("#midi-download"), musicxmlDownload: $("#musicxml-download"),
};

const acceptedExtensions = ["mp3", "wav", "m4a", "flac", "ogg"];
const formatBytes = (bytes) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const formatTime = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const midiToFrequency = (midi) => 440 * Math.pow(2, (midi - 69) / 12);
const noteName = (midi) => `${["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][midi % 12]}${Math.floor(midi / 12) - 1}`;

function showError(message) {
  elements.error.textContent = message;
  elements.error.hidden = !message;
}

function chooseFile(file) {
  showError("");
  if (!file) return;
  const extension = file.name.split(".").pop().toLowerCase();
  if (!acceptedExtensions.includes(extension) && !file.type.startsWith("audio/")) {
    showError("Please choose an MP3, WAV, M4A, FLAC, or OGG audio file.");
    return;
  }
  if (file.size > CONFIG.MAX_FILE_BYTES) {
    showError("That file is larger than 50 MB. Please choose a shorter or compressed recording.");
    return;
  }
  state.file = file;
  elements.fileName.textContent = file.name;
  elements.fileSize.textContent = formatBytes(file.size);
  elements.dropZone.hidden = true;
  elements.selectedFile.hidden = false;
  elements.submit.disabled = false;
}

function clearFile() {
  state.file = null;
  elements.fileInput.value = "";
  elements.dropZone.hidden = false;
  elements.selectedFile.hidden = true;
  elements.submit.disabled = true;
  showError("");
}

elements.dropZone.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", () => chooseFile(elements.fileInput.files[0]));
elements.removeFile.addEventListener("click", clearFile);
["dragenter", "dragover"].forEach((eventName) => elements.dropZone.addEventListener(eventName, (event) => {
  event.preventDefault(); elements.dropZone.classList.add("dragging");
}));
["dragleave", "drop"].forEach((eventName) => elements.dropZone.addEventListener(eventName, (event) => {
  event.preventDefault(); elements.dropZone.classList.remove("dragging");
}));
elements.dropZone.addEventListener("drop", (event) => chooseFile(event.dataTransfer.files[0]));

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.file) return;
  elements.uploadCard.hidden = true;
  elements.results.hidden = true;
  elements.process.hidden = false;
  state.abortController = new AbortController();
  try {
    if (CONFIG.API_BASE_URL) await submitToApi();
    else await runDemo();
  } catch (error) {
    if (error.name === "AbortError") return reset();
    elements.process.hidden = true;
    elements.uploadCard.hidden = false;
    showError(error.message || "We couldn't process that recording. Please try again.");
  }
});

async function submitToApi() {
  const formData = new FormData();
  formData.append("audio", state.file);
  updateProgress(5, "upload", "Uploading your recording…");
  const response = await fetch(`${CONFIG.API_BASE_URL}/api/jobs`, { method: "POST", body: formData, signal: state.abortController.signal });
  if (!response.ok) throw new Error(await apiError(response));
  const job = await response.json();
  state.jobId = job.id;
  while (true) {
    await delay(CONFIG.POLL_INTERVAL_MS, state.abortController.signal);
    const statusResponse = await fetch(`${CONFIG.API_BASE_URL}/api/jobs/${encodeURIComponent(state.jobId)}`, { signal: state.abortController.signal });
    if (!statusResponse.ok) throw new Error(await apiError(statusResponse));
    const status = await statusResponse.json();
    updateProgress(status.progress || 0, status.stage, status.message);
    if (status.status === "failed") throw new Error(status.error || "Transcription failed.");
    if (status.status === "complete") return showResults(status.result);
  }
}

async function apiError(response) {
  try { const body = await response.json(); return body.error || body.detail || `Request failed (${response.status}).`; }
  catch { return `Request failed (${response.status}).`; }
}

function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => { clearTimeout(timer); reject(new DOMException("Cancelled", "AbortError")); }, { once: true });
  });
}

async function runDemo() {
  const phases = [
    [12, "upload", "Uploading your recording…"], [34, "separate", "Separating the lead vocal…"],
    [67, "detect", "Listening for pitch…"], [90, "transcribe", "Writing the notes…"], [100, "transcribe", "Melody ready"],
  ];
  for (const [progress, stage, message] of phases) {
    updateProgress(progress, stage, message);
    await delay(progress === 100 ? 350 : 700, state.abortController.signal);
  }
  showResults(createDemoResult());
}

function updateProgress(progress, stage, message) {
  const value = Math.max(0, Math.min(100, progress));
  elements.progressBar.style.width = `${value}%`;
  elements.progressPercent.textContent = `${Math.round(value)}%`;
  if (message) elements.processTitle.textContent = message;
  const order = ["upload", "separate", "detect", "transcribe"];
  const current = Math.max(0, order.indexOf(stage));
  document.querySelectorAll("#process-steps li").forEach((item, index) => {
    item.classList.toggle("complete", index < current || value === 100);
    item.classList.toggle("active", index === current && value < 100);
  });
}

function createDemoResult() {
  const pitches = [60, 62, 64, 67, 64, 62, 60, 64, 67, 69, 67, 64, 62, 60];
  let cursor = 0;
  const notes = pitches.map((midi, index) => {
    const duration = index % 4 === 3 ? .75 : .42;
    const item = { midi_note: midi, start_time: cursor, duration, velocity: 76 + (index % 4) * 7 };
    cursor += duration + .08;
    return item;
  });
  return { notes, duration: cursor, midi_url: "", musicxml_url: "", demo: true };
}

function showResults(result) {
  state.notes = result.notes || [];
  state.duration = result.duration || Math.max(0, ...state.notes.map((note) => note.start_time + note.duration));
  elements.process.hidden = true;
  elements.results.hidden = false;
  elements.noteCount.textContent = state.notes.length;
  elements.durationLabel.textContent = formatTime(state.duration);
  elements.totalTime.textContent = formatTime(state.duration);
  elements.resultSummary.textContent = result.demo ? "Demo transcription ready. Connect the API to process the selected file." : "We found the notes in your recording.";
  const pitches = state.notes.map((note) => note.midi_note);
  elements.rangeLabel.textContent = pitches.length ? `${noteName(Math.min(...pitches))}–${noteName(Math.max(...pitches))}` : "—";
  setDownload(elements.midiDownload, result.midi_url, result.demo);
  setDownload(elements.musicxmlDownload, result.musicxml_url, result.demo);
  renderPianoRoll();
  elements.results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setDownload(element, url, demo) {
  if (url) { element.href = new URL(url, CONFIG.API_BASE_URL || location.href).href; element.removeAttribute("aria-disabled"); }
  else { element.removeAttribute("href"); element.setAttribute("aria-disabled", "true"); element.title = demo ? "Downloads become available when the API is connected." : "This file was not generated."; }
}

function renderPianoRoll() {
  elements.pianoRoll.replaceChildren();
  if (!state.notes.length) return;
  const pitches = state.notes.map((note) => note.midi_note);
  const low = Math.min(...pitches) - 2;
  const high = Math.max(...pitches) + 2;
  state.notes.forEach((note, index) => {
    const block = document.createElement("span");
    block.className = "roll-note";
    block.dataset.index = index;
    block.title = `${noteName(note.midi_note)} · ${note.duration.toFixed(2)}s`;
    block.style.left = `${(note.start_time / state.duration) * 100}%`;
    block.style.width = `${Math.max(0.7, (note.duration / state.duration) * 100)}%`;
    block.style.bottom = `${((note.midi_note - low) / (high - low)) * 88 + 3}%`;
    elements.pianoRoll.appendChild(block);
  });
}

let audioContext;
function getAudioContext() { audioContext ||= new (window.AudioContext || window.webkitAudioContext)(); return audioContext; }
function scheduleNote(note, delaySeconds) {
  const context = getAudioContext();
  const start = context.currentTime + Math.max(0, delaySeconds);
  const duration = Math.min(note.duration, 3);
  const gain = context.createGain();
  const profile = elements.sound.value;
  const oscillators = [];
  const settings = profile === "bell" ? [["sine", 1], ["sine", 2.01], ["sine", 3.99]] : profile === "organ" ? [["sine", 1], ["sine", 2], ["sine", .5]] : profile === "synth" ? [["sawtooth", 1], ["triangle", 1.005]] : [["triangle", 1], ["sine", 2]];
  const peak = Math.min(.18, (note.velocity || 80) / 1270) / settings.length;
  gain.gain.setValueAtTime(.0001, start);
  gain.gain.exponentialRampToValueAtTime(peak, start + .015);
  if (profile === "organ") gain.gain.setValueAtTime(peak, start + duration * .8);
  else gain.gain.exponentialRampToValueAtTime(.0001, start + Math.max(.08, duration));
  gain.connect(context.destination);
  settings.forEach(([type, ratio]) => {
    const oscillator = context.createOscillator(); oscillator.type = type; oscillator.frequency.value = midiToFrequency(note.midi_note) * ratio;
    oscillator.connect(gain); oscillator.start(start); oscillator.stop(start + duration + .05); oscillators.push(oscillator);
  });
  state.voices.push(...oscillators);
}

function startPlayback(from = state.pausedAt) {
  stopVoices();
  state.playing = true;
  state.pausedAt = from >= state.duration ? 0 : from;
  state.startedAt = performance.now() - state.pausedAt * 1000;
  elements.play.textContent = "❚❚";
  elements.play.setAttribute("aria-label", "Pause melody");
  state.notes.filter((note) => note.start_time + note.duration >= state.pausedAt).forEach((note) => {
    scheduleNote(note, Math.max(0, note.start_time - state.pausedAt));
  });
  tick();
}

function pausePlayback() {
  state.pausedAt = Math.min(state.duration, (performance.now() - state.startedAt) / 1000);
  state.playing = false; stopVoices(); cancelAnimationFrame(state.animationFrame);
  elements.play.textContent = "▶"; elements.play.setAttribute("aria-label", "Play melody");
}

function stopVoices() { state.voices.forEach((voice) => { try { voice.stop(); } catch {} }); state.voices = []; }
function tick() {
  if (!state.playing) return;
  const elapsed = (performance.now() - state.startedAt) / 1000;
  if (elapsed >= state.duration) { state.pausedAt = 0; pausePlayback(); updateTimeline(0); return; }
  updateTimeline(elapsed);
  document.querySelectorAll(".roll-note").forEach((block, index) => {
    const note = state.notes[index]; block.classList.toggle("active", elapsed >= note.start_time && elapsed < note.start_time + note.duration);
  });
  state.animationFrame = requestAnimationFrame(tick);
}

function updateTimeline(seconds) {
  elements.timeline.value = state.duration ? Math.round((seconds / state.duration) * 1000) : 0;
  elements.currentTime.textContent = formatTime(seconds);
}

elements.play.addEventListener("click", () => state.playing ? pausePlayback() : startPlayback());
elements.timeline.addEventListener("input", () => {
  const position = (Number(elements.timeline.value) / 1000) * state.duration;
  const wasPlaying = state.playing; if (wasPlaying) pausePlayback(); state.pausedAt = position; updateTimeline(position); if (wasPlaying) startPlayback(position);
});
elements.sound.addEventListener("change", () => { if (state.playing) startPlayback((performance.now() - state.startedAt) / 1000); });
elements.cancel.addEventListener("click", () => state.abortController?.abort());
elements.startOver.addEventListener("click", reset);

function reset() {
  state.abortController?.abort(); pausePlayback(); clearFile(); state.notes = []; state.duration = 0; state.jobId = null;
  updateTimeline(0); elements.results.hidden = true; elements.process.hidden = true; elements.uploadCard.hidden = false;
  elements.uploadCard.scrollIntoView({ behavior: "smooth", block: "center" });
}
