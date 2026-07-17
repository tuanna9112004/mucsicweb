from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav")
    MAX_FILE_SIZE_BYTES: int = 30 * 1024 * 1024  # 30 MB
    MAX_DURATION_SECONDS: float = 90.0

    TARGET_SAMPLE_RATE: int = 22050

    MIN_TARGET_BPM: int = 135
    MAX_TARGET_BPM: int = 140
    DEFAULT_TARGET_BPM: int = 138

    MERGE_GAP_MS: float = 40.0
    MIN_NOTE_DURATION_MS: float = 60.0
    MIN_NOTE_CONFIDENCE: float = 0.25

    QUANTIZE_UNITS_BEATS: dict = field(
        default_factory=lambda: {"none": None, "1/4": 1.0, "1/8": 0.5, "1/16": 0.25}
    )

    PIPELINE_VERSION: str = "1.0.0"


settings = Settings()
