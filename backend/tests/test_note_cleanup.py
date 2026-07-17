import pytest

from app.core.errors import NoMelodyDetectedError
from app.pipeline.note_cleanup import clean_notes
from tests.conftest import make_note


def test_merges_short_fragment_into_longer_note_within_gap():
    notes = [
        make_note(pitch=60, onset=0.0, offset=1.0, model_amplitude=0.8),
        make_note(pitch=60, onset=1.01, offset=1.05, model_amplitude=0.9),
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 1
    assert result[0].original.onset_seconds == 0.0
    assert result[0].original.offset_seconds == 1.05
    assert result[0].merged is True


def test_does_not_merge_repeated_notes_of_similar_duration():
    notes = [
        make_note(pitch=74, onset=1.045, offset=1.579, model_amplitude=0.47),
        make_note(pitch=74, onset=1.579, offset=2.045, model_amplitude=0.48),
        make_note(pitch=74, onset=2.045, offset=2.474, model_amplitude=0.49),
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 3


def test_does_not_merge_when_gap_too_large():
    notes = [make_note(pitch=60, onset=0.0, offset=0.5), make_note(pitch=60, onset=0.6, offset=1.0)]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 2


def test_does_not_merge_different_pitch():
    notes = [make_note(pitch=60, onset=0.0, offset=0.5), make_note(pitch=61, onset=0.51, offset=1.0)]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert len(result) == 2


def test_filters_short_notes():
    notes = [
        make_note(pitch=60, onset=0.0, offset=0.05),
        make_note(pitch=62, onset=0.2, offset=0.8),
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=60, min_confidence=0.0)

    assert len(result) == 1
    assert result[0].pitch_midi == 62


def test_filters_low_confidence_notes():
    notes = [
        make_note(pitch=60, onset=0.0, offset=0.5, model_amplitude=0.1),
        make_note(pitch=62, onset=0.6, offset=1.1, model_amplitude=0.9),
    ]

    result = clean_notes(notes, merge_gap_ms=40, min_duration_ms=0, min_confidence=0.25)

    assert len(result) == 1
    assert result[0].pitch_midi == 62


def test_raises_when_no_notes_survive_filtering():
    notes = [make_note(pitch=60, onset=0.0, offset=0.01, model_amplitude=0.9)]

    with pytest.raises(NoMelodyDetectedError):
        clean_notes(notes, merge_gap_ms=40, min_duration_ms=60, min_confidence=0.25)


def test_raises_when_input_is_empty():
    with pytest.raises(NoMelodyDetectedError):
        clean_notes([], merge_gap_ms=40, min_duration_ms=60, min_confidence=0.25)


def test_does_not_mutate_input_notes():
    a = make_note(pitch=60, onset=0.0, offset=1.0)
    b = make_note(pitch=60, onset=1.01, offset=1.05)
    original_a_offset = a.original.offset_seconds

    clean_notes([a, b], merge_gap_ms=40, min_duration_ms=0, min_confidence=0.0)

    assert a.original.offset_seconds == original_a_offset
