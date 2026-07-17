async function parseJsonOrThrow(response) {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const err = new Error((data && data.error && data.error.message) || "Lỗi không xác định.");
    err.code = data && data.error && data.error.code;
    err.status = response.status;
    throw err;
  }
  return data;
}

export async function getHealth() {
  const res = await fetch("/api/health");
  return parseJsonOrThrow(res);
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: formData });
  return parseJsonOrThrow(res);
}

export async function startAnalysis(jobId, targetBpm, quantize) {
  const res = await fetch(`/api/jobs/${jobId}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_bpm: targetBpm, quantize }),
  });
  return parseJsonOrThrow(res);
}

export async function getJobStatus(jobId) {
  const res = await fetch(`/api/jobs/${jobId}`);
  return parseJsonOrThrow(res);
}

export async function cancelJob(jobId) {
  const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" });
  return parseJsonOrThrow(res);
}

export function midiDownloadUrl(jobId) {
  return `/api/jobs/${jobId}/download/midi`;
}

export function jsonDownloadUrl(jobId) {
  return `/api/jobs/${jobId}/download/json`;
}
