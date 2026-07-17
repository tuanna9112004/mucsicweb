from app.pipeline.note_models import Note


def retime_notes_to_target_bpm(notes: list[Note], target_bpm: int) -> list[Note]:
    """Tính lại start_time_seconds/end_time_seconds theo tempo đích, dựa trên vị trí
    beat đã quantize. Vì vị trí lưu theo beat, đây là scale tuyến tính đơn giản và
    không ảnh hưởng cao độ.
    """
    beat_duration_target = 60.0 / target_bpm
    for note in notes:
        start = note.start_beat * beat_duration_target
        duration = note.duration_beats * beat_duration_target
        note.start_time_seconds = start
        note.end_time_seconds = start + duration
    return notes
