const TRACK_COLORS = {
  full: "#9aa0ab",
  melody: "#3457d5",
  monophonic_melody: "#3457d5",
  bass: "#d5346c",
};

const TRACK_DRAW_ORDER = ["full", "melody", "monophonic_melody", "bass"];

const PIXELS_PER_SECOND = 40;
const PIXELS_PER_SEMITONE = 4;
const NOTE_HEIGHT = 3;

export function renderPianoRoll(canvasEl, tracks) {
  const allNotes = [];
  tracks.forEach((track) => {
    track.notes.forEach((note) => {
      allNotes.push({ ...note, trackType: track.track_type });
    });
  });

  const ctx = canvasEl.getContext("2d");

  if (allNotes.length === 0) {
    canvasEl.width = 400;
    canvasEl.height = 80;
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    return;
  }

  const maxTime = Math.max(...allNotes.map((n) => n.offset_seconds_target));
  const minPitch = Math.min(...allNotes.map((n) => n.pitch_midi));
  const maxPitch = Math.max(...allNotes.map((n) => n.pitch_midi));

  const width = Math.max(400, Math.ceil(maxTime * PIXELS_PER_SECOND) + 20);
  const height = Math.max(120, (maxPitch - minPitch + 4) * PIXELS_PER_SEMITONE);

  canvasEl.width = width;
  canvasEl.height = height;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fafbfc";
  ctx.fillRect(0, 0, width, height);

  function pitchToY(pitch) {
    return height - (pitch - minPitch + 2) * PIXELS_PER_SEMITONE;
  }

  const sortedNotes = [...allNotes].sort(
    (a, b) => TRACK_DRAW_ORDER.indexOf(a.trackType) - TRACK_DRAW_ORDER.indexOf(b.trackType)
  );

  sortedNotes.forEach((note) => {
    const x = note.onset_seconds_target * PIXELS_PER_SECOND;
    const w = Math.max(2, (note.offset_seconds_target - note.onset_seconds_target) * PIXELS_PER_SECOND);
    const y = pitchToY(note.pitch_midi);
    ctx.fillStyle = TRACK_COLORS[note.trackType] || "#9aa0ab";
    ctx.fillRect(x, y, w, NOTE_HEIGHT);
  });
}
