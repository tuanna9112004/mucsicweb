import json

from app.pipeline.json_export import build_analysis_result, midi_number_to_note_name, write_analysis_json
from app.pipeline.note_models import Note


def test_midi_number_to_note_name():
    assert midi_number_to_note_name(60) == "C4"
    assert midi_number_to_note_name(69) == "A4"
    assert midi_number_to_note_name(61) == "C#4"


def test_build_analysis_result_matches_expected_shape():
    note = Note(pitch_midi=64, start_time_seconds=1.25, end_time_seconds=1.72, confidence=0.87)
    note.start_beat = 2.0
    note.duration_beats = 1.0
    note.start_beat_raw = 1.9
    note.duration_beats_raw = 0.95
    note.quantized = True

    result = build_analysis_result(
        original_filename="sample.mp3",
        duration_seconds=45.2,
        detected_bpm=100.4,
        target_bpm=138,
        quantization="1/8",
        notes=[note],
    )

    assert result.original_filename == "sample.mp3"
    assert result.detected_bpm == 100.4
    assert result.target_bpm == 138
    assert result.quantization == "1/8"
    assert result.note_count == 1
    assert result.processing_status == "completed"
    assert result.notes[0].note == "E4"
    assert result.notes[0].midi_number == 64
    assert result.notes[0].quantized is True


def test_write_analysis_json_produces_expected_field_names(tmp_path):
    note = Note(pitch_midi=60, start_time_seconds=0.0, end_time_seconds=0.45, confidence=0.91)
    note.start_beat = 0.0
    note.duration_beats = 1.0

    result = build_analysis_result(
        original_filename="sample.mp3",
        duration_seconds=32.0,
        detected_bpm=100.0,
        target_bpm=138,
        quantization="none",
        notes=[note],
    )
    output_path = tmp_path / "out.json"

    write_analysis_json(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["original_filename"] == "sample.mp3"
    assert data["note_count"] == 1
    assert data["notes"][0]["note"] == "C4"
    assert data["notes"][0]["midi_number"] == 60
    assert data["notes"][0]["start_time_seconds"] == 0.0
