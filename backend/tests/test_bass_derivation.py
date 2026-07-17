from app.music.bass_derivation import derive_bass_track
from tests.conftest import make_note


def test_separates_bass_register_adaptively_not_fixed_g3():
    # Bass cụm quanh midi 36-40, melody cụm quanh midi 70-76 — khoảng cách lớn,
    # Otsu threshold phải tách rõ 2 cụm này mà không cần biết trước ngưỡng G3(55).
    notes = [
        make_note(pitch=36, onset=0.0, offset=1.0),
        make_note(pitch=38, onset=1.0, offset=2.0),
        make_note(pitch=40, onset=2.0, offset=3.0),
        make_note(pitch=70, onset=0.0, offset=1.0),
        make_note(pitch=72, onset=1.0, offset=2.0),
        make_note(pitch=76, onset=2.0, offset=3.0),
    ]

    result = derive_bass_track(notes)

    assert [n.pitch_midi for n in result] == [36, 38, 40]


def test_keeps_bass_below_g3_even_though_g3_is_not_hardcoded():
    # Nốt bass ở midi 30 (dưới G3=55 rất xa) vẫn phải được giữ trong track bass,
    # không bị loại bởi bất kỳ ngưỡng cố định nào.
    notes = [
        make_note(pitch=30, onset=0.0, offset=1.0),
        make_note(pitch=32, onset=1.0, offset=2.0),
        make_note(pitch=68, onset=0.0, offset=1.0),
        make_note(pitch=71, onset=1.0, offset=2.0),
    ]

    result = derive_bass_track(notes)

    pitches = [n.pitch_midi for n in result]
    assert 30 in pitches
    assert 32 in pitches


def test_returns_empty_when_pitch_range_too_narrow_for_bass_split():
    notes = [make_note(pitch=60, onset=0.0, offset=1.0), make_note(pitch=61, onset=1.0, offset=2.0)]

    result = derive_bass_track(notes)

    assert result == []


def test_returns_empty_for_empty_input():
    assert derive_bass_track([]) == []
