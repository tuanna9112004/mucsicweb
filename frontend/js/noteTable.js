const LOW_MODEL_SCORE_THRESHOLD = 0.4;

function formatNumber(value) {
  return value.toFixed(2);
}

export function renderNoteTable(tbodyEl, notes) {
  tbodyEl.innerHTML = "";
  notes.forEach((note, index) => {
    const tr = document.createElement("tr");
    if (note.model_score < LOW_MODEL_SCORE_THRESHOLD) {
      tr.classList.add("row-low-confidence");
    }

    const duration = note.offset_seconds_target - note.onset_seconds_target;
    const cells = [
      index + 1,
      note.note_name,
      note.pitch_midi,
      formatNumber(note.onset_seconds_target),
      formatNumber(note.offset_seconds_target),
      formatNumber(duration),
      formatNumber(note.onset_beat_quantized),
      `${Math.round(note.model_score * 100)}%`,
    ];

    cells.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });

    tbodyEl.appendChild(tr);
  });
}

export function renderChordTable(tbodyEl, chords) {
  tbodyEl.innerHTML = "";
  chords.forEach((chord) => {
    const tr = document.createElement("tr");
    const cells = [
      chord.start_time_seconds.toFixed(2),
      chord.end_time_seconds.toFixed(2),
      chord.chord,
      chord.bass || "-",
      `${Math.round(chord.confidence * 100)}%`,
    ];
    cells.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });
    tbodyEl.appendChild(tr);
  });
}
