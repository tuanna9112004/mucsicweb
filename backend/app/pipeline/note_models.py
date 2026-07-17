from dataclasses import dataclass


@dataclass
class Note:
    pitch_midi: int
    start_time_seconds: float
    end_time_seconds: float
    confidence: float

    start_beat_raw: float = 0.0
    duration_beats_raw: float = 0.0
    start_beat: float = 0.0
    duration_beats: float = 0.0
    quantized: bool = False
    merged: bool = False

    @property
    def duration_seconds(self) -> float:
        return self.end_time_seconds - self.start_time_seconds
