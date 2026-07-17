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
