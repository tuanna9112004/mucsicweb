import dataclasses

import pytest

from app.music.note_models import OriginalTiming
from tests.conftest import make_note


def test_original_timing_is_frozen():
    timing = OriginalTiming(onset_seconds=1.0, offset_seconds=2.0)

    with pytest.raises(dataclasses.FrozenInstanceError):
        timing.onset_seconds = 5.0


def test_with_target_timing_does_not_mutate_original():
    note = make_note(pitch=60, onset=1.0, offset=2.0)
    original_onset_before = note.original.onset_seconds
    original_offset_before = note.original.offset_seconds

    retimed = note.with_target_timing(onset_seconds=10.0, offset_seconds=12.0)

    assert note.original.onset_seconds == original_onset_before
    assert note.original.offset_seconds == original_offset_before
    assert retimed.original.onset_seconds == original_onset_before  # cùng timing gốc
    assert retimed.onset_seconds_target == 10.0
    assert retimed.offset_seconds_target == 12.0
    assert retimed is not note


def test_duration_seconds_original_computed_correctly():
    note = make_note(onset=1.25, offset=1.72)

    assert note.original.duration_seconds == pytest.approx(0.47)
