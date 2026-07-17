import pytest


def _upload_fixture(api_client, synth_melody_path):
    with open(synth_melody_path, "rb") as f:
        response = api_client.post(
            "/api/upload",
            files={"file": ("synth_melody_120bpm.wav", f, "audio/wav")},
        )
    assert response.status_code == 200
    return response.json()["job_id"]


@pytest.mark.slow
def test_full_pipeline_flow_upload_analyze_poll_download(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    analyze_response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": 138, "quantize": "1/8"},
    )
    assert analyze_response.status_code == 200

    status_response = api_client.get(f"/api/jobs/{job_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "done"
    assert status_data["progress_pct"] == 100
    assert status_data["result_summary"]["metadata"]["analysis_mode"] == "melody_quick"
    assert status_data["result_summary"]["metadata"]["target_bpm"] == 138
    assert all(step["status"] == "done" for step in status_data["steps"])

    full_track = next(t for t in status_data["result_summary"]["tracks"] if t["track_type"] == "full")
    assert full_track["note_count"] == 8

    notes_response = api_client.get(f"/api/jobs/{job_id}/notes")
    assert notes_response.status_code == 200
    assert len(notes_response.json()) == 8

    midi_response = api_client.get(f"/api/jobs/{job_id}/download/full_quantized")
    assert midi_response.status_code == 200
    assert midi_response.headers["content-type"] == "audio/midi"

    json_response = api_client.get(f"/api/jobs/{job_id}/download/json")
    assert json_response.status_code == 200
    assert json_response.headers["content-type"] == "application/json"

    downloads_response = api_client.get(f"/api/jobs/{job_id}/downloads")
    assert downloads_response.status_code == 200
    available = downloads_response.json()
    assert "full_raw" in available
    assert "melody" in available
    assert "bass" not in available  # melody_quick không tạo bass track


def test_get_unknown_job_returns_404(api_client):
    response = api_client.get("/api/jobs/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "JOB_NOT_FOUND"
    assert body["error"]["message"]


def test_analyze_unknown_job_returns_404(api_client):
    response = api_client.post(
        "/api/jobs/does-not-exist/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": 138, "quantize": "none"},
    )

    assert response.status_code == 404


def test_analyze_rejects_out_of_range_bpm(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": 999, "quantize": "none"},
    )

    assert response.status_code == 422


def test_analyze_accepts_null_target_bpm_to_keep_original_tempo(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": None, "quantize": "none"},
    )

    assert response.status_code == 200


def test_analyze_rejects_invalid_quantize_mode(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": 138, "quantize": "1/32"},
    )

    assert response.status_code == 422


def test_analyze_rejects_invalid_analysis_mode(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "super_mode", "target_bpm": 138, "quantize": "none"},
    )

    assert response.status_code == 422


def test_analyze_returns_409_when_already_running(api_client, synth_melody_path):
    from app.core.job_models import JobStatus
    from app.core.job_store import job_store

    job_id = _upload_fixture(api_client, synth_melody_path)
    job_store.get(job_id).status = JobStatus.RUNNING

    response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": 138, "quantize": "none"},
    )

    assert response.status_code == 409


def test_analyze_returns_409_when_a_different_job_is_running(api_client, synth_melody_path):
    from app.core.job_models import JobStatus
    from app.core.job_store import job_store

    other_job_id = _upload_fixture(api_client, synth_melody_path)
    job_store.get(other_job_id).status = JobStatus.RUNNING

    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.post(
        f"/api/jobs/{job_id}/analyze",
        json={"analysis_mode": "melody_quick", "target_bpm": 138, "quantize": "none"},
    )

    assert response.status_code == 409


def test_notes_endpoint_returns_409_before_analysis_done(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.get(f"/api/jobs/{job_id}/notes")

    assert response.status_code == 409


def test_cancel_unknown_job_returns_404(api_client):
    response = api_client.post("/api/jobs/does-not-exist/cancel")

    assert response.status_code == 404


def test_cancel_known_job_returns_200(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.post(f"/api/jobs/{job_id}/cancel")

    assert response.status_code == 200


def test_download_returns_409_before_analysis_done(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.get(f"/api/jobs/{job_id}/download/full_quantized")

    assert response.status_code == 409


def test_download_unknown_file_type_returns_409(api_client, synth_melody_path):
    job_id = _upload_fixture(api_client, synth_melody_path)

    response = api_client.get(f"/api/jobs/{job_id}/download/not_a_real_type")

    assert response.status_code == 409


def test_two_uploads_produce_independent_job_ids(api_client, synth_melody_path):
    job_id_1 = _upload_fixture(api_client, synth_melody_path)
    job_id_2 = _upload_fixture(api_client, synth_melody_path)

    assert job_id_1 != job_id_2

    from app.core.job_store import job_store

    assert job_store.get(job_id_1) is not None
    assert job_store.get(job_id_2) is not None
    assert job_store.get(job_id_1).job_id != job_store.get(job_id_2).job_id
