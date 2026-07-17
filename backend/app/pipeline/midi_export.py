from pathlib import Path

import pretty_midi

from app.core.errors import MidiExportError
from app.pipeline.note_models import Note

_MIN_MIDI_NOTE_DURATION_SECONDS = 0.001
_PIANO_PROGRAM = 0  # Acoustic Grand Piano


def note_confidence_to_velocity(confidence: float) -> int:
    return int(min(max(round(confidence * 127), 1), 127))


def export_midi(notes: list[Note], target_bpm: int, output_path: Path) -> None:
    try:
        midi = pretty_midi.PrettyMIDI(initial_tempo=float(target_bpm))
        instrument = pretty_midi.Instrument(program=_PIANO_PROGRAM)

        for note in notes:
            end = max(note.end_time_seconds, note.start_time_seconds + _MIN_MIDI_NOTE_DURATION_SECONDS)
            instrument.notes.append(
                pretty_midi.Note(
                    velocity=note_confidence_to_velocity(note.confidence),
                    pitch=note.pitch_midi,
                    start=note.start_time_seconds,
                    end=end,
                )
            )

        midi.instruments.append(instrument)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi.write(str(output_path))
    except MidiExportError:
        raise
    except Exception as exc:
        raise MidiExportError("Không thể tạo file MIDI từ danh sách nốt đã phân tích.") from exc
