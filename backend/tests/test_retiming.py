import pytest

from app.pipeline.note_models import Note
from app.pipeline.retiming import retime_notes_to_target_bpm


def make_note(start_beat: float, duration_beats: float) -> Note:
    note = Note(pitch_midi=60, start_time_seconds=0.0, end_time_seconds=0.0, confidence=0.9)
    note.start_beat = start_beat
    note.duration_beats = duration_beats
    return note


def test_retime_scales_linearly_to_target_bpm():
    note = make_note(start_beat=2.0, duration_beats=1.0)

    result = retime_notes_to_target_bpm([note], target_bpm=120)

    assert result[0].start_time_seconds == pytest.approx(1.0)
    assert result[0].end_time_seconds == pytest.approx(1.5)


def test_retime_from_beat_position_to_138_bpm():
    note = make_note(start_beat=4.0, duration_beats=2.0)

    result = retime_notes_to_target_bpm([note], target_bpm=138)

    beat_duration = 60.0 / 138
    assert result[0].start_time_seconds == pytest.approx(4.0 * beat_duration)
    assert result[0].end_time_seconds == pytest.approx(6.0 * beat_duration)


def test_retime_does_not_change_relative_note_spacing():
    notes = [make_note(0.0, 1.0), make_note(1.0, 1.0), make_note(2.0, 1.0)]

    result = retime_notes_to_target_bpm(notes, target_bpm=135)

    beat_duration = 60.0 / 135
    gaps = [result[i + 1].start_time_seconds - result[i].start_time_seconds for i in range(2)]
    assert gaps == pytest.approx([beat_duration, beat_duration])
