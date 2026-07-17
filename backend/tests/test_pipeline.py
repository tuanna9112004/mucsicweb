import pretty_midi
import pytest

from app.pipeline.pipeline import run_pipeline


@pytest.mark.slow
def test_run_pipeline_end_to_end_on_fixture(synth_melody_path, tmp_path):
    result = run_pipeline(
        source_path=synth_melody_path,
        work_dir=tmp_path,
        original_filename="synth_melody_120bpm.wav",
        target_bpm=138,
        quantize_mode="1/8",
    )

    assert result.midi_path.exists()
    assert result.json_path.exists()
    assert result.analysis.note_count == 8
    assert result.analysis.detected_bpm == pytest.approx(120.0, abs=10.0)
    assert result.analysis.target_bpm == 138
    assert result.analysis.quantization == "1/8"

    midi = pretty_midi.PrettyMIDI(str(result.midi_path))
    notes = sorted(midi.instruments[0].notes, key=lambda n: n.start)
    assert len(notes) == 8

    beat_duration = 60.0 / 138
    assert notes[0].start == pytest.approx(0.0, abs=0.05)
    assert notes[-1].start == pytest.approx(7 * beat_duration, abs=0.15)
