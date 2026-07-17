import pytest
from dataclasses import replace

from app.pipeline.quantize import QUANTIZE_UNITS_BEATS, quantize_notes, resolve_monophonic_overlaps
from tests.conftest import make_note


def _with_beat(note, onset_beat_raw, duration_beats_raw):
    return replace(note, onset_beat_raw=onset_beat_raw, duration_beats_raw=duration_beats_raw)


def test_no_quantize_copies_raw_values():
    note = _with_beat(make_note(), 0.3, 0.9)

    result = quantize_notes([note], unit_beats=None)

    assert result[0].onset_beat_quantized == pytest.approx(0.3)
    assert result[0].duration_beats_quantized == pytest.approx(0.9)
    assert result[0].quantized is False


def test_quantize_quarter_snaps_to_nearest_beat():
    note = _with_beat(make_note(), 0.3, 0.9)  # start->round(0.3)=0, end->round(1.2)=1

    result = quantize_notes([note], unit_beats=1.0)

    assert result[0].onset_beat_quantized == pytest.approx(0.0)
    assert result[0].duration_beats_quantized == pytest.approx(1.0)
    assert result[0].quantized is True


def test_quantize_eighth_grid():
    note = _with_beat(make_note(), 0.05, 0.4)

    result = quantize_notes([note], unit_beats=0.5)

    assert result[0].onset_beat_quantized == pytest.approx(0.0)
    assert result[0].duration_beats_quantized == pytest.approx(0.5)


def test_quantize_triplet_unit():
    assert QUANTIZE_UNITS_BEATS["1/8T"] == pytest.approx(1.0 / 3)
    assert QUANTIZE_UNITS_BEATS["1/16T"] == pytest.approx(1.0 / 6)

    note = _with_beat(make_note(), 0.0, 0.3)

    result = quantize_notes([note], unit_beats=QUANTIZE_UNITS_BEATS["1/8T"])

    assert result[0].duration_beats_quantized == pytest.approx(1.0 / 3)


def test_quantize_never_produces_zero_duration():
    note = _with_beat(make_note(), 0.24, 0.02)

    result = quantize_notes([note], unit_beats=0.25)

    assert result[0].duration_beats_quantized == pytest.approx(0.25)


def test_quantize_does_not_drop_or_alter_overlapping_chord_notes():
    # 3 nốt hợp âm cùng onset — quantize_notes KHÔNG được dedupe/xóa bất kỳ nốt
    # nào trong số này, khác hẳn resolve_monophonic_overlaps (chỉ dùng cho melody).
    notes = [
        _with_beat(make_note(pitch=60), 0.0, 1.0),
        _with_beat(make_note(pitch=64), 0.0, 1.0),
        _with_beat(make_note(pitch=67), 0.0, 1.0),
    ]

    result = quantize_notes(notes, unit_beats=0.5)

    assert len(result) == 3
    assert all(n.onset_beat_quantized == pytest.approx(0.0) for n in result)
    assert {n.pitch_midi for n in result} == {60, 64, 67}


def test_quantize_preserves_overlapping_notes_different_pitch():
    # Nốt chồng thời gian (khác cao độ) là dữ liệu polyphonic hợp lệ, không được cắt/xóa.
    a = _with_beat(make_note(pitch=60), 0.0, 2.0)
    b = _with_beat(make_note(pitch=64), 0.5, 1.0)  # chồng lấn với a

    result = quantize_notes([a, b], unit_beats=0.5)

    assert len(result) == 2
    pitch_60 = next(n for n in result if n.pitch_midi == 60)
    pitch_64 = next(n for n in result if n.pitch_midi == 64)
    assert pitch_60.duration_beats_quantized == pytest.approx(2.0)  # không bị cắt ngắn


def test_quantize_does_not_mutate_raw_fields():
    note = _with_beat(make_note(), 0.3, 0.9)

    result = quantize_notes([note], unit_beats=1.0)

    assert note.onset_beat_quantized == 0.0  # note gốc không bị đổi
    assert result[0] is not note


def test_resolve_monophonic_overlaps_trims_overlap_between_consecutive_notes():
    note_a = _with_beat(make_note(pitch=60), 0.0, 1.8)
    note_b = _with_beat(make_note(pitch=62), 1.0, 1.0)

    quantized = quantize_notes([note_a, note_b], unit_beats=1.0)
    result = resolve_monophonic_overlaps(quantized, unit_beats=1.0)

    a, b = sorted(result, key=lambda n: n.onset_beat_quantized)
    assert a.onset_beat_quantized == pytest.approx(0.0)
    assert a.duration_beats_quantized == pytest.approx(1.0)
    assert b.onset_beat_quantized == pytest.approx(1.0)


def test_resolve_monophonic_overlaps_dedups_identical_onset():
    low_confidence = _with_beat(make_note(pitch=60, model_amplitude=0.4), 0.95, 0.3)
    high_confidence = _with_beat(make_note(pitch=62, model_amplitude=0.8), 1.05, 0.3)

    quantized = quantize_notes([low_confidence, high_confidence], unit_beats=1.0)
    result = resolve_monophonic_overlaps(quantized, unit_beats=1.0)

    assert len(result) == 1
    assert result[0].model_amplitude == pytest.approx(0.8)
