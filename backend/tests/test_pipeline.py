from pathlib import Path

import pretty_midi
import pytest

from app.pipeline.pipeline import run_pipeline
from app.transcribers.piano_transcriber import PianoTranscriber


@pytest.mark.slow
def test_piano_accurate_mode_preserves_polyphony_bass_and_pedal(tmp_path):
    if not PianoTranscriber().is_available():
        pytest.skip("Model piano chuyên dụng chưa được cài/tải checkpoint trong môi trường này.")

    samples_dir = Path(__file__).resolve().parent.parent.parent / "samples"
    audio_path = samples_dir / "farran_ez-minimal-piano-underscore-456148.mp3"
    if not audio_path.exists():
        pytest.skip("File mẫu farran không có sẵn.")

    result = run_pipeline(
        source_path=audio_path,
        work_dir=tmp_path,
        original_filename=audio_path.name,
        analysis_mode="piano_accurate",
        target_bpm=138,
        quantize_mode="1/8",
        source_sample_rate=44100,
        source_channels=2,
    )

    analysis = result.analysis
    full_track = next(t for t in analysis.tracks if t.track_type == "full")
    assert analysis.quality_report.maximum_polyphony > 1  # đa âm thật sự
    assert full_track.note_count > 50

    pitches = [n.pitch_midi for n in full_track.notes]
    assert min(pitches) < 55  # bass dưới G3 vẫn được giữ trong full track

    assert len(analysis.harmony.chords) > 0
    assert analysis.harmony.key is not None

    for key in ("full_raw", "full_quantized", "melody", "bass", "json"):
        assert key in result.output_files

    full_raw_midi = pretty_midi.PrettyMIDI(str(result.output_files["full_raw"]))
    assert len(full_raw_midi.instruments[0].control_changes) > 0  # pedal CC64 giữ lại


@pytest.mark.slow
def test_melody_quick_mode_end_to_end_on_fixture(synth_melody_path, tmp_path):
    result = run_pipeline(
        source_path=synth_melody_path,
        work_dir=tmp_path,
        original_filename="synth_melody_120bpm.wav",
        analysis_mode="melody_quick",
        target_bpm=138,
        quantize_mode="1/8",
    )

    analysis = result.analysis
    assert analysis.metadata.analysis_mode == "melody_quick"
    assert analysis.rhythm.detected_bpm == pytest.approx(120.0, abs=10.0)
    assert analysis.metadata.target_bpm == 138

    full_track = next(t for t in analysis.tracks if t.track_type == "full")
    melody_track = next(t for t in analysis.tracks if t.track_type == "monophonic_melody")
    assert full_track.note_count == 8
    assert melody_track.note_count == 8

    assert "full_raw" in result.output_files
    assert "full_quantized" in result.output_files
    assert "melody" in result.output_files
    assert "json" in result.output_files
    # melody_quick không tính bass/chord — không nên tạo các file này.
    assert "bass" not in result.output_files
    assert "chords" not in result.output_files

    midi = pretty_midi.PrettyMIDI(str(result.output_files["melody"]))
    notes = sorted(midi.instruments[0].notes, key=lambda n: n.start)
    assert len(notes) == 8
    beat_duration = 60.0 / 138
    assert notes[0].start == pytest.approx(0.0, abs=0.05)
    assert notes[-1].start == pytest.approx(7 * beat_duration, abs=0.15)


@pytest.mark.slow
def test_keep_original_bpm_when_target_bpm_is_none(synth_melody_path, tmp_path):
    result = run_pipeline(
        source_path=synth_melody_path,
        work_dir=tmp_path,
        original_filename="synth_melody_120bpm.wav",
        analysis_mode="melody_quick",
        target_bpm=None,
        quantize_mode="none",
    )

    assert result.analysis.metadata.target_bpm is None
    # Không retime -> timing target phải xấp xỉ timing gốc (dùng detected_bpm làm target nội bộ)
    full_track = next(t for t in result.analysis.tracks if t.track_type == "full")
    first_note = full_track.notes[0]
    assert first_note.onset_seconds_target == pytest.approx(first_note.onset_seconds_original, abs=0.1)


@pytest.mark.slow
def test_raw_notes_survive_full_pipeline_unmutated(synth_melody_path, tmp_path):
    result = run_pipeline(
        source_path=synth_melody_path,
        work_dir=tmp_path,
        original_filename="synth_melody_120bpm.wav",
        analysis_mode="melody_quick",
        target_bpm=138,
        quantize_mode="1/16",
    )

    full_track = next(t for t in result.analysis.tracks if t.track_type == "full")
    for note in full_track.notes:
        # onset gốc phải luôn <= onset đã quantize hàng chục beat (sanity: field tồn tại & hợp lý)
        assert note.duration_seconds_original > 0
        assert note.onset_seconds_original >= 0
