from pathlib import Path

from basic_pitch.inference import predict

from app.music.note_models import Note, OriginalTiming
from app.transcribers.base import BaseTranscriber, TranscriptionResult


def _clip01(value: float) -> float:
    return float(min(max(value, 0.0), 1.0))


def amplitude_to_velocity(amplitude: float) -> int:
    return int(min(max(round(amplitude * 127), 1), 127))


class BasicPitchTranscriber(BaseTranscriber):
    """Fallback transcriber — dùng Basic Pitch cho cả 'melody_quick' và làm dự
    phòng cho 'piano_accurate' khi PianoTranscriber không khả dụng.

    QUAN TRỌNG: hàm này trả về TOÀN BỘ note event thô từ Basic Pitch, kể cả khi
    chúng đa âm/chồng lấn — không áp dụng skyline hay lọc pitch ở đây. Việc rút
    gọn thành một dòng giai điệu là trách nhiệm của app.music.melody_derivation,
    chạy sau bước transcribe này.
    """

    name = "basic_pitch"

    def is_available(self) -> bool:
        return True

    def transcribe(self, audio_path: Path, work_dir: Path) -> TranscriptionResult:
        _, _, note_events = predict(str(audio_path))

        notes = [
            Note(
                pitch_midi=int(pitch_midi),
                original=OriginalTiming(onset_seconds=float(start), offset_seconds=float(end)),
                model_amplitude=_clip01(amplitude),
                velocity_estimate=amplitude_to_velocity(amplitude),
                source_model=self.name,
            )
            for start, end, pitch_midi, amplitude, _pitch_bend in note_events
        ]
        return TranscriptionResult(notes=notes, pedal_events=[])
