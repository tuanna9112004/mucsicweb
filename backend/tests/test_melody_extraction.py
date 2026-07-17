import pytest

from app.pipeline.melody_extraction import extract_raw_notes, select_melody_skyline
from app.pipeline.note_models import Note


def make_note(pitch=60, start=0.0, end=0.5, confidence=0.9) -> Note:
    return Note(pitch_midi=pitch, start_time_seconds=start, end_time_seconds=end, confidence=confidence)


def test_skyline_passes_through_non_overlapping_notes():
    notes = [make_note(60, 0.0, 0.5), make_note(62, 0.5, 1.0)]

    result = select_melody_skyline(notes)

    assert [n.pitch_midi for n in result] == [60, 62]
    assert result[0].end_time_seconds == 0.5
    assert result[1].start_time_seconds == 0.5


def test_skyline_higher_note_wins_partial_overlap():
    low = make_note(60, 0.0, 1.0)
    high = make_note(72, 0.5, 1.5)

    result = select_melody_skyline([low, high])

    assert len(result) == 2
    assert result[0].pitch_midi == 60
    assert result[0].end_time_seconds == pytest.approx(0.5)
    assert result[1].pitch_midi == 72
    assert result[1].start_time_seconds == pytest.approx(0.5)


def test_skyline_higher_note_wins_when_it_starts_first():
    high = make_note(72, 0.0, 1.0)
    low = make_note(60, 0.2, 0.8)  # nằm hoàn toàn trong high, cao độ thấp hơn

    result = select_melody_skyline([high, low])

    assert len(result) == 1
    assert result[0].pitch_midi == 72
    assert result[0].start_time_seconds == 0.0
    assert result[0].end_time_seconds == 1.0


def test_skyline_drops_lower_note_fully_engulfed():
    high = make_note(72, 0.0, 1.0)
    low = make_note(60, 0.1, 0.9)

    result = select_melody_skyline([high, low])

    assert len(result) == 1
    assert result[0].pitch_midi == 72


@pytest.mark.slow
def test_extract_raw_notes_matches_known_pitches(synth_melody_path, synth_melody_ground_truth):
    notes = extract_raw_notes(synth_melody_path)

    expected_pitches = [pitch for pitch, _start_beat, _duration_beats in synth_melody_ground_truth["notes"]]
    assert [note.pitch_midi for note in notes] == expected_pitches

    bpm = synth_melody_ground_truth["bpm"]
    beat_duration = 60.0 / bpm
    for note, (_pitch, start_beat, duration_beats) in zip(notes, synth_melody_ground_truth["notes"]):
        expected_start = start_beat * beat_duration
        expected_duration = duration_beats * beat_duration
        assert note.start_time_seconds == pytest.approx(expected_start, abs=0.05)
        assert note.duration_seconds == pytest.approx(expected_duration, abs=0.1)
        assert 0.0 <= note.confidence <= 1.0
