from dataclasses import dataclass
from pathlib import Path

import pretty_midi

from app.core.errors import MidiExportError
from app.music.note_models import ChordSpan, Note, PedalEvent

_MIN_MIDI_NOTE_DURATION_SECONDS = 0.03
_PIANO_PROGRAM = 0  # Acoustic Grand Piano
_PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_CHORD_VOICING_VELOCITY = 70
_CHORD_BASE_OCTAVE_PITCH = 60  # C4


@dataclass
class MidiNoteEvent:
    onset_seconds: float
    offset_seconds: float
    pitch_midi: int
    velocity: int


def notes_to_midi_events(notes: list[Note], timing: str) -> list[MidiNoteEvent]:
    """timing: "original" (timing gốc chưa xử lý gì) hoặc "target" (sau quantize +
    đổi tempo). Luôn đảm bảo offset > onset (không tạo nốt độ dài 0/âm)."""
    events = []
    for note in notes:
        if timing == "original":
            onset, offset = note.original.onset_seconds, note.original.offset_seconds
        elif timing == "target":
            onset, offset = note.onset_seconds_target, note.offset_seconds_target
        else:
            raise ValueError(f"timing không hợp lệ: {timing}")

        offset = max(offset, onset + _MIN_MIDI_NOTE_DURATION_SECONDS)
        events.append(
            MidiNoteEvent(
                onset_seconds=onset, offset_seconds=offset, pitch_midi=note.pitch_midi, velocity=note.velocity_estimate
            )
        )
    return events


def _resolve_same_pitch_overlaps(events: list[MidiNoteEvent]) -> list[MidiNoteEvent]:
    """Hai nốt CÙNG cao độ chồng thời gian có thể gây stuck-note ở một số phần mềm
    (note-off bị khớp nhầm note-on). Cắt nốt trước để không chồng lên nốt sau CÙNG
    cao độ — không đụng đến các nốt khác cao độ (hợp âm chồng nhau là bình thường).
    """
    by_pitch: dict[int, list[MidiNoteEvent]] = {}
    for event in events:
        by_pitch.setdefault(event.pitch_midi, []).append(event)

    resolved: list[MidiNoteEvent] = []
    for group in by_pitch.values():
        group.sort(key=lambda e: e.onset_seconds)
        for i in range(len(group) - 1):
            if group[i].offset_seconds > group[i + 1].onset_seconds:
                group[i] = MidiNoteEvent(
                    onset_seconds=group[i].onset_seconds,
                    offset_seconds=group[i + 1].onset_seconds,
                    pitch_midi=group[i].pitch_midi,
                    velocity=group[i].velocity,
                )
        resolved.extend(group)
    return resolved


def _pitch_class_to_number(name: str) -> int:
    return _PITCH_CLASS_NAMES.index(name)


def _nearest_pitch_for_class(pitch_class_name: str, base_pitch: int) -> int:
    pitch_class = _pitch_class_to_number(pitch_class_name)
    base_octave_root = base_pitch - (base_pitch % 12)
    candidate = base_octave_root + pitch_class
    options = [candidate - 12, candidate, candidate + 12]
    return min(options, key=lambda option: abs(option - base_pitch))


def chord_spans_to_midi_events(chords: list[ChordSpan], time_scale: float = 1.0) -> list[MidiNoteEvent]:
    """Chuyển timeline hợp âm thành các block chord (giữ nguyên các pitch-class,
    voicing gần quãng tám C4) để có thể xuất thành file MIDI nghe thử được.
    `time_scale` dùng khi cần quy đổi timeline hợp âm (vốn tính theo giây gốc)
    sang cùng trục thời gian với track đã đổi tempo — xem json_export/pipeline.
    """
    events = []
    for chord in chords:
        if chord.chord_symbol == "N" or not chord.pitch_classes:
            continue
        onset = chord.start_time_seconds * time_scale
        offset = chord.end_time_seconds * time_scale
        for pitch_class_name in chord.pitch_classes:
            pitch = _nearest_pitch_for_class(pitch_class_name, _CHORD_BASE_OCTAVE_PITCH)
            events.append(
                MidiNoteEvent(
                    onset_seconds=onset, offset_seconds=offset, pitch_midi=pitch, velocity=_CHORD_VOICING_VELOCITY
                )
            )
    return events


def write_midi_file(
    events: list[MidiNoteEvent],
    output_path: Path,
    tempo_bpm: float,
    track_name: str,
    pedal_events: list[PedalEvent] | None = None,
) -> None:
    try:
        midi = pretty_midi.PrettyMIDI(initial_tempo=float(tempo_bpm))
        instrument = pretty_midi.Instrument(program=_PIANO_PROGRAM, name=track_name)

        safe_events = _resolve_same_pitch_overlaps(events)
        for event in sorted(safe_events, key=lambda e: e.onset_seconds):
            if event.offset_seconds <= event.onset_seconds:
                continue
            instrument.notes.append(
                pretty_midi.Note(
                    velocity=event.velocity,
                    pitch=event.pitch_midi,
                    start=event.onset_seconds,
                    end=event.offset_seconds,
                )
            )

        if pedal_events:
            for pedal in pedal_events:
                instrument.control_changes.append(
                    pretty_midi.ControlChange(number=64, value=127, time=pedal.onset_seconds)
                )
                instrument.control_changes.append(
                    pretty_midi.ControlChange(number=64, value=0, time=pedal.offset_seconds)
                )
            instrument.control_changes.sort(key=lambda cc: cc.time)

        midi.instruments.append(instrument)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi.write(str(output_path))
    except MidiExportError:
        raise
    except Exception as exc:
        raise MidiExportError(f"Không thể tạo file MIDI ({track_name}).") from exc
