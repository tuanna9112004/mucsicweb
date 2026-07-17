from app.music.key_detection import detect_key
from tests.conftest import make_note


def test_detects_c_major_from_c_major_scale_notes():
    # Thang C major (C D E F G A B), lặp lại theo tỷ lệ giống Krumhansl-Kessler
    # profile — dùng độ dài note để tạo trọng số khác nhau theo bậc thang.
    scale_pitches = [60, 62, 64, 65, 67, 69, 71]
    weights = [3.0, 1.0, 2.0, 1.0, 2.5, 1.0, 1.0]
    notes = []
    t = 0.0
    for pitch, weight in zip(scale_pitches, weights):
        notes.append(make_note(pitch=pitch, onset=t, offset=t + weight))
        t += weight

    result = detect_key(notes)

    assert result is not None
    assert result.key_name == "C Major"
    assert result.relative_key_name == "A Minor"
    assert 0.0 <= result.confidence <= 1.0


def test_returns_none_for_empty_input():
    assert detect_key([]) is None
