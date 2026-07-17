import librosa
import pytest

from app.pipeline.tempo_beats import detect_tempo_and_beats


@pytest.mark.slow
def test_detect_tempo_matches_known_bpm(synth_melody_path, synth_melody_ground_truth):
    y, sr = librosa.load(str(synth_melody_path), sr=22050, mono=True)

    result = detect_tempo_and_beats(y, sr)

    expected_bpm = synth_melody_ground_truth["bpm"]
    assert result.detected_bpm == pytest.approx(expected_bpm, abs=6.0)
    assert len(result.beat_times) >= 4
