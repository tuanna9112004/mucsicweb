export const state = {
  file: null,
  jobId: null,
  targetBpm: 138,
  quantize: "1/8",
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
