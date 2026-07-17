from app.music.note_models import Note


def retime_notes_to_target_bpm(notes: list[Note], target_bpm: float) -> list[Note]:
    """Tính timing target (onset_seconds_target/offset_seconds_target) theo tempo
    đích, dựa trên vị trí đã quantize (onset_beat_quantized/duration_beats_quantized).

    Trả về Note MỚI cho mỗi nốt (`Note.with_target_timing`) — KHÔNG mutate note
    đầu vào, không đụng đến timing gốc (`note.original`). Vì vị trí lưu theo beat,
    đây là scale tuyến tính đơn giản và không ảnh hưởng cao độ.

    `target_bpm=None` (giữ tempo gốc) được xử lý ở tầng gọi (pipeline.py) bằng
    cách truyền detected_bpm vào làm target_bpm — hàm này luôn cần một BPM cụ thể.
    """
    beat_duration_target = 60.0 / target_bpm
    result = []
    for note in notes:
        onset = note.onset_beat_quantized * beat_duration_target
        duration = note.duration_beats_quantized * beat_duration_target
        result.append(note.with_target_timing(onset_seconds=onset, offset_seconds=onset + duration))
    return result
