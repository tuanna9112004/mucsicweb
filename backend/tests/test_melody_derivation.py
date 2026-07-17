import pytest

from app.music.melody_derivation import derive_melody_track
from tests.conftest import make_note


def test_passes_through_non_overlapping_notes_above_bass_floor():
    notes = [make_note(pitch=60, onset=0.0, offset=0.5), make_note(pitch=62, onset=0.5, offset=1.0)]

    result = derive_melody_track(notes)

    assert [n.pitch_midi for n in result] == [60, 62]


def test_higher_note_wins_partial_overlap():
    low = make_note(pitch=60, onset=0.0, offset=1.0)
    high = make_note(pitch=72, onset=0.5, offset=1.5)

    result = derive_melody_track([low, high])

    assert len(result) == 2
    assert result[0].pitch_midi == 60
    assert result[0].original.offset_seconds == pytest.approx(0.5)
    assert result[1].pitch_midi == 72
    assert result[1].original.onset_seconds == pytest.approx(0.5)


def test_higher_note_wins_when_it_starts_first():
    high = make_note(pitch=72, onset=0.0, offset=1.0)
    low = make_note(pitch=60, onset=0.2, offset=0.8)

    result = derive_melody_track([high, low])

    assert len(result) == 1
    assert result[0].pitch_midi == 72


def test_excludes_notes_below_melody_pitch_floor():
    bass_note = make_note(pitch=40, onset=0.0, offset=2.0)  # dưới G3 (55) — quá trầm cho melody
    melody_note = make_note(pitch=67, onset=0.5, offset=1.0)

    result = derive_melody_track([bass_note, melody_note])

    assert [n.pitch_midi for n in result] == [67]


def test_does_not_mutate_input_notes():
    low = make_note(pitch=60, onset=0.0, offset=1.0)
    high = make_note(pitch=72, onset=0.5, offset=1.5)
    original_low_offset = low.original.offset_seconds

    derive_melody_track([low, high])

    assert low.original.offset_seconds == original_low_offset
