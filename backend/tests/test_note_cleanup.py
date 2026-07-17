import pytest

from app.core.errors import NoMelodyDetectedError
from app.pipeline.note_cleanup import clean_notes
from app.pipeline.note_models import Note


def make_note(pitch=60, start=0.0, end=0.5, confidence=0.9) -> Note:
    return Note(pitch_midi=pitch, start_time_seconds=start, end_time_seconds=end, confidence=confidence)


def test_merges_adjacent_same_pitch_within_gap():
    notes = [
        make_note(pitch=60, start=0.0, end=0.5, confidence=0.8),
        make_note(pitch=60, start=0.51, end=1.0, confidence=0.9),  # gap 10ms <= 40ms
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 1
    assert result[0].start_time_seconds == 0.0
    assert result[0].end_time_seconds == 1.0
    assert result[0].merged is True
    expected_confidence = (0.8 * 0.5 + 0.9 * 0.49) / (0.5 + 0.49)
    assert result[0].confidence == pytest.approx(expected_confidence, rel=1e-6)


def test_does_not_merge_when_gap_too_large():
    notes = [
        make_note(pitch=60, start=0.0, end=0.5),
        make_note(pitch=60, start=0.6, end=1.0),  # gap 100ms > 40ms
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 2


def test_does_not_merge_different_pitch():
    notes = [
        make_note(pitch=60, start=0.0, end=0.5),
        make_note(pitch=61, start=0.51, end=1.0),
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 2


def test_filters_short_notes():
    notes = [
        make_note(pitch=60, start=0.0, end=0.05),  # 50ms < 60ms
        make_note(pitch=62, start=0.2, end=0.8),  # 600ms, giữ lại
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=60, min_confidence=0.0)

    assert len(result) == 1
    assert result[0].pitch_midi == 62


def test_filters_low_confidence_notes():
    notes = [
        make_note(pitch=60, start=0.0, end=0.5, confidence=0.1),
        make_note(pitch=62, start=0.6, end=1.1, confidence=0.9),
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.25)

    assert len(result) == 1
    assert result[0].pitch_midi == 62


def test_raises_when_no_notes_survive_filtering():
    notes = [make_note(pitch=60, start=0.0, end=0.01, confidence=0.9)]

    with pytest.raises(NoMelodyDetectedError):
        clean_notes(notes, merge_gap_ms=40, min_duration_ms=60, min_confidence=0.25)


def test_raises_when_input_is_empty():
    with pytest.raises(NoMelodyDetectedError):
        clean_notes([], merge_gap_ms=40, min_duration_ms=60, min_confidence=0.25)
