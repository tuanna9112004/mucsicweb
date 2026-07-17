from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import AnalyzeRequest, ErrorInfoModel, JobStatusResponse
from app.core.job_models import JobStatus, STEP_ORDER, build_step_statuses
from app.core.job_runner import execute_job
from app.core.job_store import job_store

router = APIRouter()

_JOB_NOT_FOUND_MESSAGE = "Job không tồn tại hoặc đã hết hạn (server có thể đã khởi động lại)."


@router.post("/api/jobs/{job_id}/analyze")
def analyze(job_id: str, request: AnalyzeRequest, background_tasks: BackgroundTasks) -> dict:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND_MESSAGE)
    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Đã có một tác vụ đang chạy cho job này.")

    job.cancel_requested = False
    job.error = None
    background_tasks.add_task(execute_job, job, request.target_bpm, request.quantize)
    return {"status": "queued"}


@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND_MESSAGE)

    steps = build_step_statuses(job.current_step_index, job.status)
    if job.status == JobStatus.DONE:
        progress_pct = 100
    else:
        progress_pct = round((job.current_step_index + 1) / len(STEP_ORDER) * 100)
        progress_pct = max(0, min(100, progress_pct))

    processing_time_seconds = None
    if job.started_at is not None and job.finished_at is not None:
        processing_time_seconds = job.finished_at - job.started_at

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        steps=steps,
        progress_pct=progress_pct,
        error=ErrorInfoModel(code=job.error.code, message=job.error.message) if job.error else None,
        result_summary=job.analysis,
        processing_time_seconds=processing_time_seconds,
    )


@router.get("/api/jobs/{job_id}/notes")
def get_job_notes(job_id: str) -> list:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND_MESSAGE)
    if job.analysis is None:
        raise HTTPException(status_code=409, detail="Job chưa có kết quả phân tích.")
    return [note.model_dump() for note in job.analysis.notes]


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND_MESSAGE)
    job.cancel_requested = True
    return {"status": "cancel_requested"}
