import pytest

from app.pipeline.note_models import Note
from app.pipeline.quantize import quantize_notes


def make_note(start_beat_raw: float, duration_beats_raw: float, confidence: float = 0.9) -> Note:
    note = Note(pitch_midi=60, start_time_seconds=0.0, end_time_seconds=0.0, confidence=confidence)
    note.start_beat_raw = start_beat_raw
    note.duration_beats_raw = duration_beats_raw
    return note


def test_no_quantize_copies_raw_values():
    note = make_note(0.3, 0.9)

    result = quantize_notes([note], unit_beats=None)

    assert result[0].start_beat == pytest.approx(0.3)
    assert result[0].duration_beats == pytest.approx(0.9)
    assert result[0].quantized is False


def test_quantize_quarter_snaps_to_nearest_beat():
    note = make_note(0.3, 0.9)  # start->round(0.3)=0, end->round(1.2)=1

    result = quantize_notes([note], unit_beats=1.0)

    assert result[0].start_beat == pytest.approx(0.0)
    assert result[0].duration_beats == pytest.approx(1.0)
    assert result[0].quantized is True


def test_quantize_eighth_grid():
    note = make_note(0.05, 0.4)  # start->round(0.1)*0.5=0.0, end->round(0.9)*0.5=0.5

    result = quantize_notes([note], unit_beats=0.5)

    assert result[0].start_beat == pytest.approx(0.0)
    assert result[0].duration_beats == pytest.approx(0.5)


def test_quantize_never_produces_zero_duration():
    note = make_note(0.24, 0.02)  # start và end snap về cùng vạch lưới 0.25

    result = quantize_notes([note], unit_beats=0.25)

    assert result[0].duration_beats == pytest.approx(0.25)


def test_quantize_trims_overlap_between_consecutive_notes():
    note_a = make_note(0.0, 1.8)  # snap -> start=0, end=round(1.8)=2 -> duration 2
    note_b = make_note(1.0, 1.0)  # snap -> start=1, end=round(2.0)=2 -> duration 1

    result = quantize_notes([note_a, note_b], unit_beats=1.0)

    a, b = sorted(result, key=lambda n: n.start_beat)
    assert a.start_beat == pytest.approx(0.0)
    assert a.duration_beats == pytest.approx(1.0)  # bị trim từ 2.0 để không chồng b
    assert b.start_beat == pytest.approx(1.0)
    assert b.duration_beats == pytest.approx(1.0)


def test_quantize_dedups_notes_that_snap_to_identical_start_beat():
    # Hai nốt khác nhau nhưng đủ gần để cùng snap về start_beat=1.0 với unit=1.0 —
    # phải chỉ giữ lại một nốt (confidence cao hơn), không được để trùng start_beat.
    low_confidence = make_note(0.95, 0.3, confidence=0.4)
    high_confidence = make_note(1.05, 0.3, confidence=0.8)

    result = quantize_notes([low_confidence, high_confidence], unit_beats=1.0)

    assert len(result) == 1
    assert result[0].confidence == pytest.approx(0.8)
    assert result[0].start_beat == pytest.approx(1.0)
