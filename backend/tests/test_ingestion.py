import io
import shutil

import pytest

from app.core.errors import (
    FFmpegNotFoundError,
    FileTooLargeError,
    FileTooLongError,
    FileUnreadableError,
    UnsupportedFormatError,
)
from app.pipeline import ingestion

ALLOWED = (".mp3", ".wav")


def test_validate_extension_accepts_allowed():
    ingestion.validate_extension("song.mp3", ALLOWED)
    ingestion.validate_extension("song.WAV", ALLOWED)


def test_validate_extension_rejects_disallowed():
    with pytest.raises(UnsupportedFormatError):
        ingestion.validate_extension("song.txt", ALLOWED)


def test_validate_extension_rejects_no_extension():
    with pytest.raises(UnsupportedFormatError):
        ingestion.validate_extension("song", ALLOWED)


def test_save_upload_within_limit(tmp_path):
    data = b"x" * 1000
    dest = tmp_path / "out.bin"

    written = ingestion.save_upload(io.BytesIO(data), dest, max_bytes=2000)

    assert written == 1000
    assert dest.read_bytes() == data


def test_save_upload_exceeds_limit_raises_and_cleans_up(tmp_path):
    data = b"x" * 5000
    dest = tmp_path / "out.bin"

    with pytest.raises(FileTooLargeError):
        ingestion.save_upload(io.BytesIO(data), dest, max_bytes=2000)

    assert not dest.exists()


def test_probe_audio_on_valid_fixture(synth_melody_path):
    info = ingestion.probe_audio(synth_melody_path)

    assert info.duration_seconds == pytest.approx(4.5, abs=0.2)
    assert info.format_name


def test_probe_audio_on_garbage_file_raises_unreadable(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"this is not a valid audio file")

    with pytest.raises(FileUnreadableError):
        ingestion.probe_audio(bad)


def test_probe_audio_missing_ffprobe_raises(monkeypatch, synth_melody_path):
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(FFmpegNotFoundError):
        ingestion.probe_audio(synth_melody_path)


def test_validate_duration_within_limit():
    ingestion.validate_duration(45.0, max_seconds=90.0)


def test_validate_duration_exceeds_limit():
    with pytest.raises(FileTooLongError):
        ingestion.validate_duration(95.0, max_seconds=90.0)
