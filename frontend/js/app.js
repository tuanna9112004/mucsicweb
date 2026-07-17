import * as api from "./api.js";
import { describeError } from "./errors.js";
import { initDropzone } from "./dropzone.js";
import { loadFileIntoPlayer, revokePlayerUrl } from "./player.js";
import { renderStepper, renderProgress } from "./stepper.js";
import { renderNoteTable } from "./noteTable.js";
import { state, resetState } from "./state.js";

const POLL_INTERVAL_MS = 500;

const el = {
  ffmpegBanner: document.getElementById("ffmpeg-banner"),
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
  sectionNotes: document.getElementById("section-notes"),
  notesTableBody: document.getElementById("notes-table-body"),
  sectionDownload: document.getElementById("section-download"),
  btnDownloadMidi: document.getElementById("btn-download-midi"),
  btnDownloadJson: document.getElementById("btn-download-json"),
  btnNewAnalysis: document.getElementById("btn-new-analysis"),
};

const DEFAULT_TARGET_BPM = 138;
const DEFAULT_QUANTIZE = "1/8";

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

async function checkFfmpegHealth() {
  try {
    const health = await api.getHealth();
    el.ffmpegBanner.hidden = Boolean(health.ffmpeg_found && health.ffprobe_found);
  } catch {
    // Nếu health-check thất bại (server chưa sẵn sàng), không chặn UI — các
    // thao tác sau (upload/analyze) sẽ tự báo lỗi rõ ràng nếu thực sự có vấn đề.
  }
}

function resetConfigInputs() {
  el.selectBpm.value = String(DEFAULT_TARGET_BPM);
  el.selectQuantize.value = DEFAULT_QUANTIZE;
  state.targetBpm = DEFAULT_TARGET_BPM;
  state.quantize = DEFAULT_QUANTIZE;
}

function hideDownstreamSections() {
  el.sectionProcessing.hidden = true;
  el.sectionResults.hidden = true;
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
  const rows = [
    ["Tên file", r.original_filename],
    ["Thời lượng", formatDuration(r.duration_seconds)],
    ["Tempo gốc", `${r.detected_bpm.toFixed(1)} BPM`],
    ["Tempo đầu ra", `${r.target_bpm} BPM`],
    ["Số lượng nốt", `${r.note_count}`],
    ["Mức căn nhịp", r.quantization === "none" ? "Không căn" : r.quantization],
  ];
  if (r.estimated_key) {
    rows.push(["Tông ước lượng", r.estimated_key]);
  }
  if (statusData.processing_time_seconds != null) {
    rows.push(["Thời gian xử lý", `${statusData.processing_time_seconds.toFixed(1)}s`]);
  }
  if (r.warnings && r.warnings.length > 0) {
    rows.push(["Cảnh báo", r.warnings.join("; ")]);
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
    renderResultsSummary(buildResultsSummaryRows(statusData));
    renderNoteTable(el.notesTableBody, statusData.result_summary.notes);
    el.btnDownloadMidi.href = api.midiDownloadUrl(state.jobId);
    el.btnDownloadJson.href = api.jsonDownloadUrl(state.jobId);
    el.sectionResults.hidden = false;
    el.sectionNotes.hidden = false;
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

  try {
    await api.startAnalysis(state.jobId, state.targetBpm, state.quantize);
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
  checkFfmpegHealth();

  initDropzone({
    dropzoneEl: el.dropzone,
    fileInputEl: el.fileInput,
    browseButtonEl: el.btnBrowse,
    onFileSelected: handleFileSelected,
    onValidationError: handleValidationError,
  });

  el.btnRemoveFile.addEventListener("click", removeSelectedFile);

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
