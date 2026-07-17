from app.transcribers.base import BaseTranscriber
from app.transcribers.basic_pitch_transcriber import BasicPitchTranscriber
from app.transcribers.piano_transcriber import PianoTranscriber

_piano_transcriber = PianoTranscriber()
_basic_pitch_transcriber = BasicPitchTranscriber()


def select_transcriber(analysis_mode: str) -> tuple[BaseTranscriber, list[str]]:
    """Chọn transcriber phù hợp cho analysis_mode ("piano_accurate" | "melody_quick").

    Trả về (transcriber, warnings) — warnings ghi lại khi phải fallback (vd model
    piano chuyên dụng chưa cài/chưa có checkpoint) để hiển thị rõ cho người dùng,
    không âm thầm đổi model.
    """
    warnings: list[str] = []

    if analysis_mode == "piano_accurate":
        if _piano_transcriber.is_available():
            return _piano_transcriber, warnings
        warnings.append(
            "Không tìm thấy model piano chuyên dụng (piano_transcription_inference) hoặc "
            "checkpoint chưa được tải — dùng Basic Pitch làm dự phòng cho chế độ Piano "
            "Accurate. Kết quả polyphony/pedal có thể kém chính xác hơn model piano chuyên dụng."
        )
        return _basic_pitch_transcriber, warnings

    return _basic_pitch_transcriber, warnings
