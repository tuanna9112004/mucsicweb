from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.music.note_models import Note, PedalEvent


@dataclass
class TranscriptionResult:
    notes: list[Note]
    pedal_events: list[PedalEvent] = field(default_factory=list)


class BaseTranscriber(ABC):
    """Abstraction cho một model audio-to-notes. Cho phép model_router chọn model
    phù hợp (piano chuyên dụng hoặc Basic Pitch) mà phần còn lại của pipeline
    không cần biết chi tiết model nào đang chạy bên dưới.
    """

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """True nếu transcriber có thể chạy trong môi trường hiện tại (đã cài
        dependency, đã có checkpoint...)."""

    @abstractmethod
    def transcribe(self, audio_path: Path, work_dir: Path) -> TranscriptionResult:
        """Trả về TOÀN BỘ nốt đa âm phát hiện được — không skyline, không lọc
        pitch, không dedupe. Đây là nguồn dữ liệu gốc; mọi phép rút gọn (melody,
        bass, chord) phải là bước riêng, áp dụng SAU, trên dữ liệu đã transcribe."""
