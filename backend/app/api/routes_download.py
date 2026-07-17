from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import JobNotFoundError, JobResultNotReadyError
from app.core.job_store import job_store

router = APIRouter()

_JOB_NOT_FOUND_MESSAGE = "Job không tồn tại hoặc đã hết hạn (server có thể đã khởi động lại)."

_MEDIA_TYPES = {
    "full_raw": "audio/midi",
    "full_quantized": "audio/midi",
    "melody": "audio/midi",
    "bass": "audio/midi",
    "chords": "audio/midi",
    "json": "application/json",
}


@router.get("/api/jobs/{job_id}/download/{file_type}")
def download_file(job_id: str, file_type: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None:
        raise JobNotFoundError(_JOB_NOT_FOUND_MESSAGE)

    path = job.output_files.get(file_type)
    if path is None or not path.exists():
        raise JobResultNotReadyError(
            f"File '{file_type}' chưa sẵn sàng hoặc không tồn tại cho job này."
        )

    media_type = _MEDIA_TYPES.get(file_type, "application/octet-stream")
    return FileResponse(path, filename=path.name, media_type=media_type)


@router.get("/api/jobs/{job_id}/downloads")
def list_downloads(job_id: str) -> dict:
    """Liệt kê các file có sẵn để tải cho job này — frontend dùng để hiện đúng
    nút tải (vd không hiện nút 'Tải bass' nếu bài không có bass track riêng)."""
    job = job_store.get(job_id)
    if job is None:
        raise JobNotFoundError(_JOB_NOT_FOUND_MESSAGE)

    return {file_type: path.name for file_type, path in job.output_files.items() if path.exists()}
