from fastapi import APIRouter, BackgroundTasks

from app.api.schemas import AnalyzeRequest, ErrorInfoModel, JobStatusResponse
from app.core.errors import JobAlreadyRunningError, JobNotFoundError, JobResultNotReadyError
from app.core.job_models import JobStatus, STEP_ORDER, build_step_statuses
from app.core.job_runner import execute_job
from app.core.job_store import job_store

router = APIRouter()

_JOB_NOT_FOUND_MESSAGE = "Job không tồn tại hoặc đã hết hạn (server có thể đã khởi động lại)."


def _get_job_or_raise(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise JobNotFoundError(_JOB_NOT_FOUND_MESSAGE)
    return job


@router.post("/api/jobs/{job_id}/analyze")
def analyze(job_id: str, request: AnalyzeRequest, background_tasks: BackgroundTasks) -> dict:
    job = _get_job_or_raise(job_id)
    if job.status == JobStatus.RUNNING:
        raise JobAlreadyRunningError("Đã có một tác vụ đang chạy cho job này.")
    if job_store.has_running_job(exclude_job_id=job_id):
        raise JobAlreadyRunningError(
            "Một job khác đang được phân tích — vui lòng đợi hoàn tất trước khi bắt đầu job mới "
            "(máy chỉ chạy một tác vụ phân tích nặng tại một thời điểm)."
        )

    job.cancel_requested = False
    job.error = None
    background_tasks.add_task(execute_job, job, request.analysis_mode, request.target_bpm, request.quantize)
    return {"status": "queued"}


@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = _get_job_or_raise(job_id)

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
    job = _get_job_or_raise(job_id)
    if job.analysis is None:
        raise JobResultNotReadyError("Job chưa có kết quả phân tích.")
    full_track = next((t for t in job.analysis.tracks if t.track_type == "full"), None)
    return [note.model_dump() for note in full_track.notes] if full_track else []


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    job = _get_job_or_raise(job_id)
    job.cancel_requested = True
    return {"status": "cancel_requested"}
