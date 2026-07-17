const LOW_CONFIDENCE_THRESHOLD = 0.4;

function formatNumber(value) {
  return value.toFixed(2);
}

export function renderNoteTable(tbodyEl, notes) {
  tbodyEl.innerHTML = "";
  notes.forEach((note, index) => {
    const tr = document.createElement("tr");
    if (note.confidence < LOW_CONFIDENCE_THRESHOLD) {
      tr.classList.add("row-low-confidence");
    }

    const cells = [
      index + 1,
      note.note,
      note.midi_number,
      formatNumber(note.start_time_seconds),
      formatNumber(note.end_time_seconds),
      formatNumber(note.duration_seconds),
      formatNumber(note.start_beat),
      `${Math.round(note.confidence * 100)}%`,
    ];

    cells.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });

    tbodyEl.appendChild(tr);
  });
}
