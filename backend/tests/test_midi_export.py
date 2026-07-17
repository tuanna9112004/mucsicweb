import pretty_midi
import pytest

from app.pipeline.midi_export import export_midi, note_confidence_to_velocity
from app.pipeline.note_models import Note


def make_note(pitch: int, start: float, end: float, confidence: float = 0.9) -> Note:
    return Note(pitch_midi=pitch, start_time_seconds=start, end_time_seconds=end, confidence=confidence)


def test_note_confidence_to_velocity_bounds():
    assert note_confidence_to_velocity(0.0) == 1
    assert note_confidence_to_velocity(1.0) == 127
    assert note_confidence_to_velocity(0.5) == round(0.5 * 127)


def test_export_midi_round_trip(tmp_path):
    notes = [
        make_note(60, 0.0, 0.5, confidence=0.9),
        make_note(64, 0.5, 1.0, confidence=0.5),
    ]
    output_path = tmp_path / "out.mid"

    export_midi(notes, target_bpm=138, output_path=output_path)

    assert output_path.exists()
    loaded = pretty_midi.PrettyMIDI(str(output_path))
    assert len(loaded.instruments) == 1

    loaded_notes = sorted(loaded.instruments[0].notes, key=lambda n: n.start)
    assert len(loaded_notes) == 2
    assert loaded_notes[0].pitch == 60
    assert loaded_notes[0].start == pytest.approx(0.0, abs=1e-3)
    assert loaded_notes[0].end == pytest.approx(0.5, abs=1e-3)
    assert loaded_notes[1].pitch == 64


def test_export_midi_uses_target_tempo(tmp_path):
    notes = [make_note(60, 0.0, 0.5)]
    output_path = tmp_path / "out.mid"

    export_midi(notes, target_bpm=138, output_path=output_path)

    loaded = pretty_midi.PrettyMIDI(str(output_path))
    tempo_change_times, tempi = loaded.get_tempo_changes()
    assert tempi[0] == pytest.approx(138.0, abs=0.5)
