from pathlib import Path

from basic_pitch.inference import predict

from app.pipeline.note_models import Note

_MIN_RESIDUAL_SECONDS = 0.01  # tránh tạo mảnh nốt vụn khi trim đoạn chồng lấn


def _clip_confidence(amplitude: float) -> float:
    return float(min(max(amplitude, 0.0), 1.0))


def select_melody_skyline(notes: list[Note]) -> list[Note]:
    """Chọn một dòng giai điệu đơn âm từ các nốt đa âm bằng heuristic "skyline":
    khi hai nốt chồng lấn thời gian, giữ nốt có cao độ cao hơn cho đoạn giao nhau.

    Đây là một phép đơn giản hóa có chủ đích cho MVP — không tái tạo chính xác toàn bộ
    polyphony, chỉ nhằm trích ra một dòng giai điệu chính hợp lý.
    """
    notes_sorted = sorted(notes, key=lambda n: n.start_time_seconds)
    melody: list[Note] = []

    for note in notes_sorted:
        if not melody:
            melody.append(note)
            continue

        last = melody[-1]
        if note.start_time_seconds >= last.end_time_seconds:
            melody.append(note)
            continue

        if note.pitch_midi >= last.pitch_midi:
            if note.start_time_seconds - last.start_time_seconds >= _MIN_RESIDUAL_SECONDS:
                last.end_time_seconds = note.start_time_seconds
                melody.append(note)
            else:
                melody[-1] = note
        else:
            if note.end_time_seconds - last.end_time_seconds >= _MIN_RESIDUAL_SECONDS:
                note.start_time_seconds = last.end_time_seconds
                melody.append(note)
            # else: note nằm hoàn toàn trong last -> bỏ qua

    return melody


def extract_raw_notes(audio_path: Path) -> list[Note]:
    """Chạy Basic Pitch trên file audio đã chuẩn hóa, trả về danh sách nốt giai điệu
    chính (đã áp dụng skyline để đảm bảo đơn âm), sắp xếp theo thời gian bắt đầu.
    """
    _, _, note_events = predict(str(audio_path))

    notes = [
        Note(
            pitch_midi=int(pitch_midi),
            start_time_seconds=float(start),
            end_time_seconds=float(end),
            confidence=_clip_confidence(amplitude),
        )
        for start, end, pitch_midi, amplitude, _pitch_bend in note_events
    ]

    return select_melody_skyline(notes)
