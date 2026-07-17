import io
from dataclasses import replace

import numpy as np
import pytest
import soundfile as sf


def test_upload_valid_wav_file(api_client, synth_melody_path):
    with open(synth_melody_path, "rb") as f:
        response = api_client.post(
            "/api/upload",
            files={"file": ("synth_melody_120bpm.wav", f, "audio/wav")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "synth_melody_120bpm.wav"
    assert data["duration_seconds"] == pytest.approx(4.5, abs=0.2)
    assert "job_id" in data


def test_upload_rejects_unsupported_extension(api_client):
    response = api_client.post(
        "/api/upload",
        files={"file": ("song.txt", io.BytesIO(b"not audio"), "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_upload_rejects_file_too_large(api_client, monkeypatch):
    import app.api.routes_upload as routes_upload_module

    small_limit_settings = replace(routes_upload_module.settings, MAX_FILE_SIZE_BYTES=100)
    monkeypatch.setattr(routes_upload_module, "settings", small_limit_settings)

    big_payload = b"x" * 1000
    response = api_client.post(
        "/api/upload",
        files={"file": ("big.wav", io.BytesIO(big_payload), "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_rejects_unreadable_file(api_client):
    response = api_client.post(
        "/api/upload",
        files={"file": ("bad.wav", io.BytesIO(b"this is not a real wav file"), "audio/wav")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_UNREADABLE"


def test_upload_rejects_file_too_long(api_client, tmp_path):
    long_audio = np.zeros(int(95 * 22050), dtype=np.float32)
    long_path = tmp_path / "long.wav"
    sf.write(str(long_path), long_audio, 22050)

    with open(long_path, "rb") as f:
        response = api_client.post(
            "/api/upload",
            files={"file": ("long.wav", f, "audio/wav")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_TOO_LONG"


def test_upload_reports_ffmpeg_not_found(api_client, monkeypatch, synth_melody_path):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: None)

    with open(synth_melody_path, "rb") as f:
        response = api_client.post(
            "/api/upload",
            files={"file": ("song.wav", f, "audio/wav")},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "FFMPEG_NOT_FOUND"
