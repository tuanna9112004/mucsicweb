from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class OriginalTiming:
    """Timing gốc do transcriber trả về — bất biến (frozen).

    Không có hàm nào trong pipeline được phép ghi đè các giá trị này. Mọi thao tác
    "sửa timing" (merge, quantize, retiming) phải tạo OriginalTiming/Note mới thay
    vì mutate cái cũ.
    """

    onset_seconds: float
    offset_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.offset_seconds - self.onset_seconds


@dataclass
class Note:
    """Một nốt xuyên suốt pipeline: giữ đồng thời timing gốc (bất biến), timing đã
    quy về lưới beat (raw + quantized), và timing cuối cùng theo tempo đích.
    """

    pitch_midi: int
    original: OriginalTiming

    # Nguồn gốc dữ liệu — không gọi là "confidence" vì đây là giá trị thô của model,
    # chưa qua hiệu chỉnh (calibration) nào.
    model_amplitude: float
    velocity_estimate: int
    source_model: str  # "piano_cnn" | "basic_pitch"

    onset_beat_raw: float = 0.0
    duration_beats_raw: float = 0.0
    onset_beat_quantized: float = 0.0
    duration_beats_quantized: float = 0.0
    quantized: bool = False
    merged: bool = False

    onset_seconds_target: float = 0.0
    offset_seconds_target: float = 0.0

    def with_target_timing(self, onset_seconds: float, offset_seconds: float) -> "Note":
        """Trả về bản sao với timing target mới — không mutate note gốc."""
        return dataclass_replace(self, onset_seconds_target=onset_seconds, offset_seconds_target=offset_seconds)

    @property
    def duration_seconds_target(self) -> float:
        return self.offset_seconds_target - self.onset_seconds_target


def dataclass_replace(note: Note, **changes) -> Note:
    from dataclasses import replace

    return replace(note, **changes)


@dataclass(frozen=True)
class PedalEvent:
    onset_seconds: float
    offset_seconds: float


@dataclass
class ChordSpan:
    start_time_seconds: float
    end_time_seconds: float
    chord_symbol: str  # vd "Gm7/Bb", hoặc "N" khi không đủ dữ liệu
    root: Optional[str]
    bass: Optional[str]
    pitch_classes: list[str] = field(default_factory=list)
    confidence: float = 0.0
