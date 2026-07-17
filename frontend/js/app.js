import * as api from "./api.js";
import { describeError } from "./errors.js";
import { initDropzone } from "./dropzone.js";
import { loadFileIntoPlayer, revokePlayerUrl } from "./player.js";
import { renderStepper, renderProgress } from "./stepper.js";
import { renderNoteTable, renderChordTable } from "./noteTable.js";
import { renderPianoRoll } from "./pianoRoll.js";
import { state, resetState } from "./state.js";

const POLL_INTERVAL_MS = 500;

const el = {
  ffmpegBanner: document.getElementById("ffmpeg-banner"),
  pianoModelBanner: document.getElementById("piano-model-banner"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("file-input"),
  btnBrowse: document.getElementById("btn-browse"),
  fileError: document.getElementById("file-error"),
  fileInfo: document.getElementById("file-info"),
  fileName: document.getElementById("file-name"),
  fileSize: document.getElementById("file-size"),
  fileFormat: document.getElementById("file-format"),
  fileDuration: document.getElementById("file-duration"),
  audioPlayer: document.getElementById("audio-player"),
  btnRemoveFile: document.getElementById("btn-remove-file"),
  sectionConfig: document.getElementById("section-config"),
  selectMode: document.getElementById("select-mode"),
  modeHint: document.getElementById("mode-hint"),
  chkKeepOriginalBpm: document.getElementById("chk-keep-original-bpm"),
  selectBpm: document.getElementById("select-bpm"),
  selectQuantize: document.getElementById("select-quantize"),
  btnAnalyze: document.getElementById("btn-analyze"),
  btnResetConfig: document.getElementById("btn-reset-config"),
  sectionProcessing: document.getElementById("section-processing"),
  stepper: document.getElementById("stepper"),
  progressFill: document.getElementById("progress-fill"),
  btnCancel: document.getElementById("btn-cancel"),
  processingError: document.getElementById("processing-error"),
  sectionResults: document.getElementById("section-results"),
  resultsSummary: document.getElementById("results-summary"),
  qualityWarnings: document.getElementById("quality-warnings"),
  sectionHarmony: document.getElementById("section-harmony"),
  chordsTableBody: document.getElementById("chords-table-body"),
  sectionPianoroll: document.getElementById("section-pianoroll"),
  pianoRollCanvas: document.getElementById("piano-roll-canvas"),
  sectionNotes: document.getElementById("section-notes"),
  trackTabs: document.getElementById("track-tabs"),
  notesTableBody: document.getElementById("notes-table-body"),
  sectionDownload: document.getElementById("section-download"),
  downloadButtons: document.getElementById("download-buttons"),
  btnNewAnalysis: document.getElementById("btn-new-analysis"),
};

const DEFAULT_TARGET_BPM = 138;
const DEFAULT_QUANTIZE = "none";
const DEFAULT_MODE = "piano_accurate";

const MODE_HINTS = {
  piano_accurate:
    "Giữ toàn bộ nốt đa âm (hợp âm, bass, pedal). Tách thêm track melody/bass, nhận diện hợp âm và tông. Chậm hơn.",
  melody_quick:
    "Chỉ trích xuất một dòng giai điệu đơn âm (monophonic_melody), không tính hợp âm/tông. Nhanh hơn.",
};

const DOWNLOAD_LABELS = {
  full_raw: "MIDI Full (timing gốc)",
  full_quantized: "MIDI Full (đã căn nhịp)",
  melody: "MIDI Melody",
  bass: "MIDI Bass",
  chords: "MIDI Chords",
  json: "JSON phân tích",
};

let currentTrackType = null;

function formatFileSize(bytes) {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.round(bytes / 1024)} KB`;
}

function formatDuration(seconds) {
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function showError(bannerEl, code, fallbackMessage) {
  bannerEl.textContent = describeError(code, fallbackMessage);
  bannerEl.hidden = false;
}

function hideError(bannerEl) {
  bannerEl.hidden = true;
  bannerEl.textContent = "";
}

async function checkHealth() {
  try {
    const health = await api.getHealth();
    el.ffmpegBanner.hidden = Boolean(health.ffmpeg_found && health.ffprobe_found);
    el.pianoModelBanner.hidden = Boolean(health.piano_model_available);
  } catch {
    // Nếu health-check thất bại (server chưa sẵn sàng), không chặn UI — các
    // thao tác sau (upload/analyze) sẽ tự báo lỗi rõ ràng nếu thực sự có vấn đề.
  }
}

function updateModeHint() {
  el.modeHint.textContent = MODE_HINTS[el.selectMode.value] || "";
}

function resetConfigInputs() {
  el.selectMode.value = DEFAULT_MODE;
  el.selectBpm.value = String(DEFAULT_TARGET_BPM);
  el.selectQuantize.value = DEFAULT_QUANTIZE;
  el.chkKeepOriginalBpm.checked = false;
  el.selectBpm.disabled = false;
  state.analysisMode = DEFAULT_MODE;
  state.targetBpm = DEFAULT_TARGET_BPM;
  state.quantize = DEFAULT_QUANTIZE;
  updateModeHint();
}

function hideDownstreamSections() {
  el.sectionProcessing.hidden = true;
  el.sectionResults.hidden = true;
  el.sectionHarmony.hidden = true;
  el.sectionPianoroll.hidden = true;
  el.sectionNotes.hidden = true;
  el.sectionDownload.hidden = true;
}

async function handleFileSelected(file) {
  hideError(el.fileError);
  state.file = file;

  el.fileName.textContent = file.name;
  el.fileSize.textContent = formatFileSize(file.size);
  el.fileFormat.textContent = file.name.split(".").pop().toUpperCase();
  el.fileDuration.textContent = "…";
  el.fileInfo.hidden = false;
  el.sectionConfig.hidden = true;
  hideDownstreamSections();

  const duration = await loadFileIntoPlayer(el.audioPlayer, file);
  el.fileDuration.textContent = formatDuration(duration);

  try {
    const upload = await api.uploadFile(file);
    state.jobId = upload.job_id;
    resetConfigInputs();
    el.sectionConfig.hidden = false;
  } catch (err) {
    showError(el.fileError, err.code, err.message);
    el.fileInfo.hidden = true;
    revokePlayerUrl(el.audioPlayer);
    state.file = null;
  }
}

function handleValidationError(code) {
  showError(el.fileError, code);
}

function removeSelectedFile() {
  revokePlayerUrl(el.audioPlayer);
  el.fileInfo.hidden = true;
  el.sectionConfig.hidden = true;
  hideDownstreamSections();
  hideError(el.fileError);
  resetState();
}

function buildResultsSummaryRows(statusData) {
  const r = statusData.result_summary;
  const rhythm = r.rhythm;
  const harmony = r.harmony;
  const rows = [
    ["Tên file", r.metadata.filename],
    ["Thời lượng", formatDuration(r.metadata.duration_seconds)],
    ["Chế độ", r.metadata.analysis_mode],
    ["Tempo gốc", rhythm.detected_bpm != null ? `${rhythm.detected_bpm.toFixed(1)} BPM` : "Không rõ"],
    ["Tempo đầu ra", r.metadata.target_bpm != null ? `${r.metadata.target_bpm} BPM` : "Giữ nguyên tempo gốc"],
    ["Nhịp (time signature)", rhythm.time_signature ? `${rhythm.time_signature} (${Math.round((rhythm.confidence || 0) * 100)}%)` : "Không xác định"],
    ["Mức căn nhịp", r.metadata.quantization === "none" ? "Không căn" : r.metadata.quantization],
  ];
  if (harmony.key) {
    rows.push(["Tông ước lượng", `${harmony.key} (họ hàng: ${harmony.relative_key}, ${Math.round((harmony.confidence || 0) * 100)}%)`]);
  }
  r.tracks.forEach((track) => {
    rows.push([`Số nốt (${track.track_type})`, `${track.note_count}`]);
  });
  if (statusData.processing_time_seconds != null) {
    rows.push(["Thời gian xử lý", `${statusData.processing_time_seconds.toFixed(1)}s`]);
  }
  return rows;
}

function renderResultsSummary(rows) {
  el.resultsSummary.innerHTML = "";
  rows.forEach(([label, value]) => {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    el.resultsSummary.appendChild(dt);
    el.resultsSummary.appendChild(dd);
  });
}

function renderQualityWarnings(qualityReport) {
  const messages = [];
  if (qualityReport.manual_review_recommended) {
    messages.push("Khuyến nghị kiểm tra thủ công lại kết quả (độ tin cậy trung bình không cao).");
  }
  messages.push(...(qualityReport.warnings || []));

  if (messages.length === 0) {
    el.qualityWarnings.hidden = true;
    return;
  }
  el.qualityWarnings.textContent = messages.join(" ");
  el.qualityWarnings.hidden = false;
}

function renderTrackTabs(tracks) {
  el.trackTabs.innerHTML = "";
  tracks.forEach((track, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tab-button";
    button.textContent = `${track.track_type} (${track.note_count})`;
    if (index === 0) {
      button.classList.add("tab-active");
      currentTrackType = track.track_type;
    }
    button.addEventListener("click", () => {
      currentTrackType = track.track_type;
      Array.from(el.trackTabs.children).forEach((btn) => btn.classList.remove("tab-active"));
      button.classList.add("tab-active");
      const selected = tracks.find((t) => t.track_type === currentTrackType);
      renderNoteTable(el.notesTableBody, selected.notes);
    });
    el.trackTabs.appendChild(button);
  });
}

async function renderDownloadButtons() {
  el.downloadButtons.innerHTML = "";
  let available;
  try {
    available = await api.getAvailableDownloads(state.jobId);
  } catch {
    return;
  }
  Object.keys(available).forEach((fileType) => {
    const a = document.createElement("a");
    a.href = api.downloadUrl(state.jobId, fileType);
    a.setAttribute("download", "");
    a.className = fileType === "full_quantized" ? "btn-primary" : "btn-secondary";
    a.textContent = DOWNLOAD_LABELS[fileType] || fileType;
    el.downloadButtons.appendChild(a);
  });
}

function stopPolling() {
  if (state.pollTimerId) {
    clearInterval(state.pollTimerId);
    state.pollTimerId = null;
  }
}

function onAnalysisFinished() {
  stopPolling();
  el.btnAnalyze.disabled = false;
  el.btnCancel.disabled = true;
}

async function pollJobStatus() {
  let statusData;
  try {
    statusData = await api.getJobStatus(state.jobId);
  } catch (err) {
    onAnalysisFinished();
    showError(el.processingError, err.code, err.message);
    return;
  }

  renderStepper(el.stepper, statusData.steps);
  renderProgress(el.progressFill, statusData.progress_pct);

  if (statusData.status === "done") {
    onAnalysisFinished();
    const r = statusData.result_summary;

    renderResultsSummary(buildResultsSummaryRows(statusData));
    renderQualityWarnings(r.quality_report);
    el.sectionResults.hidden = false;

    if (r.harmony.chords && r.harmony.chords.length > 0) {
      renderChordTable(el.chordsTableBody, r.harmony.chords);
      el.sectionHarmony.hidden = false;
    }

    renderPianoRoll(el.pianoRollCanvas, r.tracks);
    el.sectionPianoroll.hidden = false;

    renderTrackTabs(r.tracks);
    const firstTrack = r.tracks[0];
    if (firstTrack) {
      renderNoteTable(el.notesTableBody, firstTrack.notes);
    }
    el.sectionNotes.hidden = false;

    await renderDownloadButtons();
    el.sectionDownload.hidden = false;
  } else if (statusData.status === "error" || statusData.status === "cancelled") {
    onAnalysisFinished();
    showError(el.processingError, statusData.error && statusData.error.code, statusData.error && statusData.error.message);
  }
}

async function startAnalysis() {
  hideError(el.processingError);
  hideDownstreamSections();
  el.sectionProcessing.hidden = false;
  el.btnAnalyze.disabled = true;
  el.btnCancel.disabled = false;

  const targetBpm = el.chkKeepOriginalBpm.checked ? null : state.targetBpm;

  try {
    await api.startAnalysis(state.jobId, state.analysisMode, targetBpm, state.quantize);
  } catch (err) {
    onAnalysisFinished();
    showError(el.processingError, err.code, err.message);
    return;
  }

  stopPolling();
  state.pollTimerId = setInterval(pollJobStatus, POLL_INTERVAL_MS);
  pollJobStatus();
}

function startNewAnalysis() {
  removeSelectedFile();
  el.fileInput.value = "";
}

function init() {
  checkHealth();

  initDropzone({
    dropzoneEl: el.dropzone,
    fileInputEl: el.fileInput,
    browseButtonEl: el.btnBrowse,
    onFileSelected: handleFileSelected,
    onValidationError: handleValidationError,
  });

  el.btnRemoveFile.addEventListener("click", removeSelectedFile);

  el.selectMode.addEventListener("change", () => {
    state.analysisMode = el.selectMode.value;
    updateModeHint();
  });
  el.chkKeepOriginalBpm.addEventListener("change", () => {
    el.selectBpm.disabled = el.chkKeepOriginalBpm.checked;
  });
  el.selectBpm.addEventListener("change", () => {
    state.targetBpm = parseInt(el.selectBpm.value, 10);
  });
  el.selectQuantize.addEventListener("change", () => {
    state.quantize = el.selectQuantize.value;
  });
  el.btnResetConfig.addEventListener("click", resetConfigInputs);

  el.btnAnalyze.addEventListener("click", startAnalysis);
  el.btnCancel.addEventListener("click", () => {
    api.cancelJob(state.jobId).catch(() => {});
  });

  el.btnNewAnalysis.addEventListener("click", startNewAnalysis);
}

init();
