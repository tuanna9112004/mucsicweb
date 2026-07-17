from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.job_store import job_store

router = APIRouter()

_JOB_NOT_FOUND_MESSAGE = "Job không tồn tại hoặc đã hết hạn (server có thể đã khởi động lại)."


@router.get("/api/jobs/{job_id}/download/midi")
def download_midi(job_id: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None or job.midi_path is None or not job.midi_path.exists():
        raise HTTPException(status_code=404, detail="File MIDI chưa sẵn sàng hoặc không tồn tại.")
    return FileResponse(job.midi_path, filename=job.midi_path.name, media_type="audio/midi")


@router.get("/api/jobs/{job_id}/download/json")
def download_json(job_id: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None or job.json_path is None or not job.json_path.exists():
        raise HTTPException(status_code=404, detail="File JSON chưa sẵn sàng hoặc không tồn tại.")
    return FileResponse(job.json_path, filename=job.json_path.name, media_type="application/json")
