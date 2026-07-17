from dataclasses import dataclass, field
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    UPLOAD_ROOT: Path = BACKEND_ROOT / "uploads"

    ALLOWED_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav")
    MAX_FILE_SIZE_BYTES: int = 30 * 1024 * 1024  # 30 MB
    MAX_DURATION_SECONDS: float = 90.0

    TARGET_SAMPLE_RATE: int = 22050

    MIN_TARGET_BPM: int = 135
    MAX_TARGET_BPM: int = 140
    DEFAULT_TARGET_BPM: int = 138

    MERGE_GAP_MS: float = 40.0
    # Chỉ gộp 2 nốt liền kề cùng cao độ khi nốt ngắn hơn có độ dài < tỷ lệ này so với
    # nốt dài hơn — phân biệt "mảnh nốt vỡ do nhiễu" (rất ngắn so với nốt chính) với
    # "nốt lặp lại có chủ đích" (độ dài tương đương nhau, không nên gộp).
    MERGE_MAX_DURATION_RATIO: float = 0.3
    MIN_NOTE_DURATION_MS: float = 60.0
    MIN_NOTE_CONFIDENCE: float = 0.25

    # Nốt dưới ngưỡng này (G3) bị loại khỏi danh sách ứng viên giai điệu trước khi
    # chạy skyline — tránh nốt bass/hợp âm giữ (sustain) bị chọn nhầm làm "giai điệu"
    # chỉ vì nó là nốt cao nhất đang vang tại thời điểm không có bè trên nào khác.
    MELODY_MIN_MIDI_PITCH: int = 55

    QUANTIZE_UNITS_BEATS: dict = field(
        default_factory=lambda: {"none": None, "1/4": 1.0, "1/8": 0.5, "1/16": 0.25}
    )

    PIPELINE_VERSION: str = "1.0.0"


settings = Settings()
