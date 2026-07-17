import soundfile as sf

from app.core.errors import FileUnreadableError
from app.pipeline.normalization import normalize_audio

import pytest


def test_normalize_audio_produces_mono_wav_at_target_rate(synth_melody_path, tmp_path):
    dest = tmp_path / "normalized.wav"

    y = normalize_audio(synth_melody_path, dest, target_sr=22050)

    assert dest.exists()
    info = sf.info(str(dest))
    assert info.samplerate == 22050
    assert info.channels == 1
    assert len(y) > 0


def test_normalize_audio_on_garbage_file_raises_unreadable(tmp_path):
    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"not an audio file")
    dest = tmp_path / "out.wav"

    with pytest.raises(FileUnreadableError):
        normalize_audio(bad, dest, target_sr=22050)
