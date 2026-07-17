import threading
from typing import Optional

from app.core.job_models import Job


class JobStore:
    """Lưu trữ một job duy nhất tại một thời điểm trong bộ nhớ — khớp phạm vi MVP
    "không xử lý nhiều tác vụ đồng thời", không cần queue.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job: Optional[Job] = None

    def set(self, job: Job) -> None:
        with self._lock:
            self._job = job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            if self._job is not None and self._job.job_id == job_id:
                return self._job
            return None

    def get_current(self) -> Optional[Job]:
        with self._lock:
            return self._job

    def reset(self) -> None:
        with self._lock:
            self._job = None


job_store = JobStore()
