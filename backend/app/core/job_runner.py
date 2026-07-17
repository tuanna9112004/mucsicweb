import logging
import time

from app.core.errors import PipelineError
from app.core.job_models import ErrorInfo, Job, JobStatus, STEP_ORDER
from app.pipeline.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def execute_job(
    job: Job,
    analysis_mode: str,
    target_bpm: float | None,
    quantize_mode: str,
) -> None:
    """Chạy pipeline phân tích cho một job và cập nhật trạng thái/tiến trình của
    job đó tại chỗ. Được gọi từ FastAPI BackgroundTasks — job là đối tượng dùng
    chung với job_store nên các cập nhật ở đây được phản ánh ngay khi client poll.
    """
    job.status = JobStatus.RUNNING
    job.current_step_index = -1
    job.started_at = time.time()
    job.finished_at = None

    def on_step(step) -> None:
        job.current_step_index = STEP_ORDER.index(step)

    def should_cancel() -> bool:
        return job.cancel_requested

    try:
        result = run_pipeline(
            source_path=job.source_path,
            work_dir=job.work_dir,
            original_filename=job.original_filename,
            analysis_mode=analysis_mode,
            target_bpm=target_bpm,
            quantize_mode=quantize_mode,
            source_sample_rate=job.sample_rate,
            source_channels=job.channels,
            on_step=on_step,
            should_cancel=should_cancel,
        )
        job.analysis = result.analysis
        job.output_files = result.output_files
        job.status = JobStatus.DONE
    except PipelineError as exc:
        job.error = ErrorInfo(code=exc.code, message=exc.user_message)
        job.status = JobStatus.CANCELLED if exc.code == "TASK_CANCELLED" else JobStatus.ERROR
    except MemoryError:
        job.error = ErrorInfo(code="OUT_OF_MEMORY", message="Không đủ bộ nhớ để xử lý file này.")
        job.status = JobStatus.ERROR
    except Exception:
        logger.exception("Lỗi không xác định khi xử lý job %s", job.job_id)
        job.error = ErrorInfo(
            code="ANALYSIS_ERROR", message="Đã xảy ra lỗi không xác định khi phân tích file."
        )
        job.status = JobStatus.ERROR
    finally:
        job.finished_at = time.time()
