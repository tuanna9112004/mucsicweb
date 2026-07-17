from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.api.schemas import UploadResponse
from app.config import settings
from app.core.errors import NoFileSelectedError
from app.core.job_models import Job, JobStatus, new_job_id
from app.core.job_store import job_store
from app.pipeline import ingestion

router = APIRouter()


@router.post("/api/upload", response_model=UploadResponse)
def upload(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise NoFileSelectedError("Chưa chọn file để tải lên.")

    ingestion.validate_extension(file.filename, settings.ALLOWED_EXTENSIONS)

    job_id = new_job_id()
    work_dir = settings.UPLOAD_ROOT / job_id
    source_path = work_dir / f"source{Path(file.filename).suffix.lower()}"

    size_bytes = ingestion.save_upload(file.file, source_path, settings.MAX_FILE_SIZE_BYTES)

    probe = ingestion.probe_audio(source_path)
    ingestion.validate_duration(probe.duration_seconds, settings.MAX_DURATION_SECONDS)

    job = Job(
        job_id=job_id,
        original_filename=file.filename,
        source_path=source_path,
        work_dir=work_dir,
        status=JobStatus.UPLOADED,
        duration_seconds=probe.duration_seconds,
        size_bytes=size_bytes,
    )
    job_store.set(job)

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        duration_seconds=probe.duration_seconds,
        size_bytes=size_bytes,
    )
