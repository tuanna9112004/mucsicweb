from app.music.chord_detection import detect_chords
from tests.conftest import make_note


def test_detects_c_major_triad_same_onset():
    # Ba nốt hợp âm C major cùng onset — không được xóa bớt nốt nào chỉ vì trùng
    # thời điểm bắt đầu (đây là hợp âm thật, không phải nhiễu trùng lặp).
    notes = [
        make_note(pitch=60, onset=0.0, offset=2.0),  # C4
        make_note(pitch=64, onset=0.0, offset=2.0),  # E4
        make_note(pitch=67, onset=0.0, offset=2.0),  # G4
    ]

    chords = detect_chords(notes, beat_times=None)

    assert len(chords) >= 1
    assert chords[0].chord_symbol == "C"
    assert chords[0].root == "C"
    assert set(chords[0].pitch_classes) == {"C", "E", "G"}


def test_detects_chord_inversion_as_slash_chord():
    # First inversion của C major: E ở bass, vẫn là hợp âm C major nhưng bass khác root.
    notes = [
        make_note(pitch=52, onset=0.0, offset=2.0),  # E3 (bass)
        make_note(pitch=55, onset=0.0, offset=2.0),  # G3
        make_note(pitch=60, onset=0.0, offset=2.0),  # C4
    ]

    chords = detect_chords(notes, beat_times=None)

    assert chords[0].chord_symbol == "C/E"
    assert chords[0].root == "C"
    assert chords[0].bass == "E"


def test_returns_no_chord_symbol_for_silence():
    chords = detect_chords([], beat_times=None)

    assert chords == []


def test_merges_adjacent_identical_chord_spans():
    # Cùng hợp âm Gm giữ liên tục qua nhiều cửa sổ 1-giây -> phải gộp thành 1 span,
    # không báo đổi hợp âm liên tục.
    notes = [
        make_note(pitch=55, onset=0.0, offset=3.0),  # G3
        make_note(pitch=58, onset=0.0, offset=3.0),  # A#3
        make_note(pitch=62, onset=0.0, offset=3.0),  # D4
    ]

    chords = detect_chords(notes, beat_times=None)

    gm_spans = [c for c in chords if c.chord_symbol == "Gm"]
    assert len(gm_spans) == 1
    assert gm_spans[0].start_time_seconds == 0.0
    assert gm_spans[0].end_time_seconds == 3.0


def test_dominant_seventh_chord_detected():
    notes = [
        make_note(pitch=60, onset=0.0, offset=1.0),  # C
        make_note(pitch=64, onset=0.0, offset=1.0),  # E
        make_note(pitch=67, onset=0.0, offset=1.0),  # G
        make_note(pitch=70, onset=0.0, offset=1.0),  # A#/Bb
    ]

    chords = detect_chords(notes, beat_times=None)

    assert chords[0].chord_symbol == "C7"
