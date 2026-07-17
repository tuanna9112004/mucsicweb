import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from app.api.schemas import AnalysisResult


class JobStatus(str, Enum):
    UPLOADED = "uploaded"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class StepKey(str, Enum):
    CHECK_FILE = "check_file"
    NORMALIZE = "normalize"
    TEMPO_BEATS = "tempo_beats"
    MELODY_ANALYSIS = "melody_analysis"
    NOTES_CONVERSION = "notes_conversion"
    CLEAN_NOTES = "clean_notes"
    QUANTIZE = "quantize"
    EXPORT = "export"


STEP_LABELS: dict[StepKey, str] = {
    StepKey.CHECK_FILE: "Đang kiểm tra file",
    StepKey.NORMALIZE: "Đang chuẩn hóa âm thanh",
    StepKey.TEMPO_BEATS: "Đang phát hiện tempo và beat",
    StepKey.MELODY_ANALYSIS: "Đang phân tích giai điệu",
    StepKey.NOTES_CONVERSION: "Đang chuyển thành nốt MIDI",
    StepKey.CLEAN_NOTES: "Đang làm sạch nốt",
    StepKey.QUANTIZE: "Đang căn nốt theo beat",
    StepKey.EXPORT: "Đang tạo file kết quả",
}

STEP_ORDER: list[StepKey] = list(StepKey)


@dataclass
class ErrorInfo:
    code: str
    message: str


@dataclass
class Job:
    job_id: str
    original_filename: str
    source_path: Path
    work_dir: Path
    status: JobStatus = JobStatus.UPLOADED
    duration_seconds: float = 0.0
    size_bytes: int = 0
    current_step_index: int = -1
    error: Optional[ErrorInfo] = None
    analysis: Optional[AnalysisResult] = None
    midi_path: Optional[Path] = None
    json_path: Optional[Path] = None
    cancel_requested: bool = False
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


def new_job_id() -> str:
    return uuid.uuid4().hex


def build_step_statuses(current_step_index: int, status: JobStatus) -> list[dict]:
    steps = []
    for i, step_key in enumerate(STEP_ORDER):
        if status == JobStatus.DONE:
            step_status = "done"
        elif status == JobStatus.ERROR and i == current_step_index:
            step_status = "error"
        elif i < current_step_index:
            step_status = "done"
        elif i == current_step_index and status == JobStatus.RUNNING:
            step_status = "active"
        else:
            step_status = "pending"
        steps.append({"key": step_key.value, "label": STEP_LABELS[step_key], "status": step_status})
    return steps
