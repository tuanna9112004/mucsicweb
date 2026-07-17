import pytest

from app.transcribers.basic_pitch_transcriber import BasicPitchTranscriber
from app.transcribers.model_router import select_transcriber
from app.transcribers.piano_transcriber import PianoTranscriber


def test_basic_pitch_transcriber_is_always_available():
    assert BasicPitchTranscriber().is_available() is True


def test_model_router_melody_quick_always_uses_basic_pitch():
    transcriber, warnings = select_transcriber("melody_quick")

    assert transcriber.name == "basic_pitch"
    assert warnings == []


def test_model_router_piano_accurate_uses_piano_model_when_available():
    transcriber, warnings = select_transcriber("piano_accurate")

    if PianoTranscriber().is_available():
        assert transcriber.name == "piano_cnn"
        assert warnings == []
    else:
        assert transcriber.name == "basic_pitch"
        assert len(warnings) == 1


@pytest.mark.slow
def test_basic_pitch_transcriber_returns_full_polyphony_no_filtering(synth_melody_path, tmp_path):
    result = BasicPitchTranscriber().transcribe(synth_melody_path, tmp_path)

    assert len(result.notes) == 8  # fixture đơn âm, khớp ground truth đã biết
    assert result.pedal_events == []
    for note in result.notes:
        assert note.source_model == "basic_pitch"
        assert 0.0 <= note.model_amplitude <= 1.0
        assert 1 <= note.velocity_estimate <= 127


@pytest.mark.slow
def test_piano_transcriber_detects_full_polyphony_and_pedal(tmp_path):
    if not PianoTranscriber().is_available():
        pytest.skip("Model piano chuyên dụng chưa được cài/tải checkpoint trong môi trường này.")

    from pathlib import Path

    samples_dir = Path(__file__).resolve().parent.parent.parent / "samples"
    audio_path = samples_dir / "farran_ez-minimal-piano-underscore-456148.mp3"
    if not audio_path.exists():
        pytest.skip("File mẫu farran không có sẵn.")

    result = PianoTranscriber().transcribe(audio_path, tmp_path)

    assert len(result.notes) > 50
    pitches = [n.pitch_midi for n in result.notes]
    assert min(pitches) < 55  # có nốt bass thật sự dưới G3, không bị lọc
    assert len(result.pedal_events) > 0
    for note in result.notes:
        assert note.source_model == "piano_cnn"
