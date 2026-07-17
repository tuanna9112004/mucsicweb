from dataclasses import replace

import pytest

from app.pipeline.retiming import retime_notes_to_target_bpm
from tests.conftest import make_note


def _with_quantized_beat(note, onset_beat, duration_beats):
    return replace(note, onset_beat_quantized=onset_beat, duration_beats_quantized=duration_beats)


def test_retime_scales_linearly_to_target_bpm():
    note = _with_quantized_beat(make_note(), 2.0, 1.0)

    result = retime_notes_to_target_bpm([note], target_bpm=120)

    assert result[0].onset_seconds_target == pytest.approx(1.0)
    assert result[0].offset_seconds_target == pytest.approx(1.5)


def test_retime_from_beat_position_to_138_bpm():
    note = _with_quantized_beat(make_note(), 4.0, 2.0)

    result = retime_notes_to_target_bpm([note], target_bpm=138)

    beat_duration = 60.0 / 138
    assert result[0].onset_seconds_target == pytest.approx(4.0 * beat_duration)
    assert result[0].offset_seconds_target == pytest.approx(6.0 * beat_duration)


def test_retime_does_not_mutate_original_or_beat_fields():
    note = _with_quantized_beat(make_note(onset=1.0, offset=1.5), 0.0, 1.0)
    original_onset = note.original.onset_seconds

    result = retime_notes_to_target_bpm([note], target_bpm=135)

    assert note.original.onset_seconds == original_onset
    assert note.onset_seconds_target == 0.0  # note gốc không bị đổi
    assert result[0] is not note
    assert result[0].original.onset_seconds == original_onset  # timing gốc vẫn giữ nguyên trên bản mới


def test_retime_does_not_change_relative_note_spacing():
    notes = [
        _with_quantized_beat(make_note(), 0.0, 1.0),
        _with_quantized_beat(make_note(), 1.0, 1.0),
        _with_quantized_beat(make_note(), 2.0, 1.0),
    ]

    result = retime_notes_to_target_bpm(notes, target_bpm=135)

    beat_duration = 60.0 / 135
    gaps = [result[i + 1].onset_seconds_target - result[i].onset_seconds_target for i in range(2)]
    assert gaps == pytest.approx([beat_duration, beat_duration])
