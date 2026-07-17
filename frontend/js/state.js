export const state = {
  file: null,
  jobId: null,
  analysisMode: "piano_accurate",
  targetBpm: 138,
  quantize: "none",
  pollTimerId: null,
};

export function resetState() {
  if (state.pollTimerId) {
    clearInterval(state.pollTimerId);
  }
  state.file = null;
  state.jobId = null;
  state.pollTimerId = null;
}
