import threading
from typing import Optional

from app.core.job_models import Job, JobStatus


class JobStore:
    """Lưu nhiều job độc lập theo job_id (dict) — một job mới KHÔNG ghi đè job
    khác đang tồn tại/đang chạy, khác với thiết kế single-slot trước đây.

    Vẫn giới hạn chỉ MỘT job được thực sự RUNNING tại một thời điểm (qua
    `has_running_job`) để tránh chạy nhiều model nặng cùng lúc trên máy người
    dùng — nhưng nhiều job có thể tồn tại song song ở trạng thái uploaded/done/error.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}

    def add(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def has_running_job(self, exclude_job_id: Optional[str] = None) -> bool:
        with self._lock:
            return any(
                job.status == JobStatus.RUNNING for job in self._jobs.values() if job.job_id != exclude_job_id
            )

    def reset(self) -> None:
        with self._lock:
            self._jobs.clear()


job_store = JobStore()
