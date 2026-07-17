def test_health_endpoint_reports_ffmpeg_status(api_client):
    response = api_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert "ffmpeg_found" in data
    assert "ffprobe_found" in data
