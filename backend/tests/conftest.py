from dataclasses import replace
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def synth_melody_path() -> Path:
    path = FIXTURES_DIR / "synth_melody_120bpm.wav"
    assert path.exists(), "Fixture missing — run: python tests/fixtures/generate_fixture.py"
    return path


@pytest.fixture(scope="session")
def synth_melody_ground_truth() -> dict:
    from tests.fixtures.generate_fixture import BPM, NOTES

    return {"bpm": BPM, "notes": NOTES}


@pytest.fixture(autouse=True)
def _reset_job_store():
    from app.core.job_store import job_store

    job_store.reset()
    yield
    job_store.reset()


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    import app.api.routes_upload as routes_upload_module
    from app.config import settings as global_settings

    test_settings = replace(global_settings, UPLOAD_ROOT=tmp_path / "uploads")
    monkeypatch.setattr(routes_upload_module, "settings", test_settings)

    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
