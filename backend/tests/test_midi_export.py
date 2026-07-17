from dataclasses import replace

import pretty_midi
import pytest

from app.music.note_models import PedalEvent
from app.pipeline.midi_export import (
    MidiNoteEvent,
    chord_spans_to_midi_events,
    notes_to_midi_events,
    write_midi_file,
)
from app.music.note_models import ChordSpan
from tests.conftest import make_note


def test_notes_to_midi_events_uses_original_timing():
    note = make_note(pitch=60, onset=1.0, offset=1.5, velocity=88)

    events = notes_to_midi_events([note], timing="original")

    assert events[0].onset_seconds == 1.0
    assert events[0].offset_seconds == 1.5
    assert events[0].velocity == 88


def test_notes_to_midi_events_uses_target_timing():
    note = make_note(pitch=60, onset=1.0, offset=1.5)
    note = replace(note, onset_seconds_target=0.0, offset_seconds_target=0.434)

    events = notes_to_midi_events([note], timing="target")

    assert events[0].onset_seconds == 0.0
    assert events[0].offset_seconds == pytest.approx(0.434)


def test_export_midi_preserves_polyphony(tmp_path):
    # Hợp âm 3 nốt cùng lúc phải xuất hiện đầy đủ trong file MIDI, không bị giảm
    # xuống 1 nốt.
    notes = [make_note(pitch=60, onset=0.0, offset=1.0), make_note(pitch=64, onset=0.0, offset=1.0), make_note(pitch=67, onset=0.0, offset=1.0)]
    events = notes_to_midi_events(notes, timing="original")
    output_path = tmp_path / "chord.mid"

    write_midi_file(events, output_path, tempo_bpm=120, track_name="Full")

    loaded = pretty_midi.PrettyMIDI(str(output_path))
    assert len(loaded.instruments[0].notes) == 3
    assert {n.pitch for n in loaded.instruments[0].notes} == {60, 64, 67}


def test_export_midi_writes_pedal_cc64(tmp_path):
    events = [MidiNoteEvent(onset_seconds=0.0, offset_seconds=1.0, pitch_midi=60, velocity=90)]
    pedal_events = [PedalEvent(onset_seconds=0.2, offset_seconds=0.8)]
    output_path = tmp_path / "pedal.mid"

    write_midi_file(events, output_path, tempo_bpm=120, track_name="Full", pedal_events=pedal_events)

    loaded = pretty_midi.PrettyMIDI(str(output_path))
    ccs = loaded.instruments[0].control_changes
    assert len(ccs) == 2
    assert all(cc.number == 64 for cc in ccs)
    values = sorted((cc.time, cc.value) for cc in ccs)
    assert values[0] == (pytest.approx(0.2), 127)
    assert values[1] == (pytest.approx(0.8), 0)


def test_export_midi_resolves_same_pitch_overlap_to_avoid_stuck_notes(tmp_path):
    # Hai nốt CÙNG cao độ chồng thời gian -> phải được cắt để không chồng, tránh
    # stuck-note. Khác cao độ chồng nhau (hợp âm) thì KHÔNG bị đụng tới.
    events = [
        MidiNoteEvent(onset_seconds=0.0, offset_seconds=1.0, pitch_midi=60, velocity=90),
        MidiNoteEvent(onset_seconds=0.5, offset_seconds=1.5, pitch_midi=60, velocity=90),
    ]
    output_path = tmp_path / "overlap.mid"

    write_midi_file(events, output_path, tempo_bpm=120, track_name="Full")

    loaded = pretty_midi.PrettyMIDI(str(output_path))
    notes = sorted(loaded.instruments[0].notes, key=lambda n: n.start)
    assert len(notes) == 2
    assert notes[0].end <= notes[1].start + 1e-6  # không chồng lấn cùng cao độ


def test_export_midi_uses_target_tempo(tmp_path):
    events = [MidiNoteEvent(onset_seconds=0.0, offset_seconds=0.5, pitch_midi=60, velocity=90)]
    output_path = tmp_path / "tempo.mid"

    write_midi_file(events, output_path, tempo_bpm=138, track_name="Full")

    loaded = pretty_midi.PrettyMIDI(str(output_path))
    _times, tempi = loaded.get_tempo_changes()
    assert tempi[0] == pytest.approx(138.0, abs=0.5)


def test_export_midi_sets_track_name(tmp_path):
    events = [MidiNoteEvent(onset_seconds=0.0, offset_seconds=0.5, pitch_midi=60, velocity=90)]
    output_path = tmp_path / "name.mid"

    write_midi_file(events, output_path, tempo_bpm=120, track_name="Bass")

    loaded = pretty_midi.PrettyMIDI(str(output_path))
    assert loaded.instruments[0].name == "Bass"


def test_chord_spans_to_midi_events_produces_block_chord():
    chord = ChordSpan(
        start_time_seconds=0.0,
        end_time_seconds=1.0,
        chord_symbol="C",
        root="C",
        bass="C",
        pitch_classes=["C", "E", "G"],
        confidence=0.9,
    )

    events = chord_spans_to_midi_events([chord])

    assert len(events) == 3
    pitch_classes_out = {e.pitch_midi % 12 for e in events}
    assert pitch_classes_out == {0, 4, 7}


def test_chord_spans_to_midi_events_skips_no_chord_symbol():
    chord = ChordSpan(
        start_time_seconds=0.0, end_time_seconds=1.0, chord_symbol="N", root=None, bass=None, pitch_classes=[], confidence=0.0
    )

    events = chord_spans_to_midi_events([chord])

    assert events == []
