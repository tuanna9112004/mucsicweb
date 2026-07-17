import json
from dataclasses import replace

from app.music.note_models import ChordSpan
from app.music.key_detection import KeyEstimate
from app.pipeline.json_export import build_analysis_result, midi_number_to_note_name, write_analysis_json
from app.pipeline.tempo_beats import BpmCandidate, TempoBeatResult
from tests.conftest import make_note


def _tempo_result():
    return TempoBeatResult(
        detected_bpm=100.0,
        beat_times=[0.0, 0.5, 1.0, 1.5],
        bpm_candidates=[BpmCandidate(bpm=100.0, score=1.0), BpmCandidate(bpm=200.0, score=0.5)],
        downbeat_times=[0.0, 1.5],
        time_signature="4/4",
        time_signature_confidence=0.7,
    )


def test_midi_number_to_note_name():
    assert midi_number_to_note_name(60) == "C4"
    assert midi_number_to_note_name(69) == "A4"
    assert midi_number_to_note_name(61) == "C#4"


def test_build_analysis_result_matches_schema_v2_shape():
    note = make_note(pitch=64, onset=1.25, offset=1.72, model_amplitude=0.87)
    note = replace(note, onset_beat_quantized=2.0, duration_beats_quantized=1.0, quantized=True)

    result = build_analysis_result(
        original_filename="sample.mp3",
        duration_seconds=45.2,
        sample_rate=44100,
        channels=2,
        analysis_mode="piano_accurate",
        target_bpm=138,
        quantization="1/8",
        tempo_result=_tempo_result(),
        key_estimate=KeyEstimate(key_name="C Major", relative_key_name="A Minor", confidence=0.8),
        chords=[
            ChordSpan(
                start_time_seconds=0.0,
                end_time_seconds=1.0,
                chord_symbol="C",
                root="C",
                bass="C",
                pitch_classes=["C", "E", "G"],
                confidence=0.9,
            )
        ],
        tracks={"full": [note], "melody": [note]},
        warnings=["cảnh báo test"],
    )

    assert result.schema_version == "2.0"
    assert result.metadata.filename == "sample.mp3"
    assert result.metadata.analysis_mode == "piano_accurate"
    assert result.rhythm.detected_bpm == 100.0
    assert result.rhythm.bpm_candidates[0].bpm == 100.0
    assert result.harmony.key == "C Major"
    assert result.harmony.chords[0].chord == "C"
    assert len(result.tracks) == 2
    full_track = next(t for t in result.tracks if t.track_type == "full")
    assert full_track.note_count == 1
    assert full_track.notes[0].note_name == "E4"
    assert full_track.notes[0].model_score == 0.87
    assert result.quality_report.warnings == ["cảnh báo test"]


def test_write_analysis_json_produces_valid_json_with_expected_field_names(tmp_path):
    note = make_note(pitch=60, onset=0.0, offset=0.45, model_amplitude=0.91)

    result = build_analysis_result(
        original_filename="sample.mp3",
        duration_seconds=32.0,
        sample_rate=22050,
        channels=1,
        analysis_mode="melody_quick",
        target_bpm=None,
        quantization="none",
        tempo_result=_tempo_result(),
        key_estimate=None,
        chords=[],
        tracks={"full": [note]},
        warnings=[],
    )
    output_path = tmp_path / "out.json"

    write_analysis_json(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["metadata"]["target_bpm"] is None
    assert data["tracks"][0]["notes"][0]["note_name"] == "C4"
    assert data["tracks"][0]["notes"][0]["onset_seconds_original"] == 0.0
    assert "model_score" in data["tracks"][0]["notes"][0]
    assert data["harmony"]["key"] is None
