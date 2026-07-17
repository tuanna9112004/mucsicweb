from app.config import settings
from app.music.note_models import Note

_MIN_RESIDUAL_SECONDS = 0.01  # tránh tạo mảnh nốt vụn khi trim đoạn chồng lấn


def derive_melody_track(notes: list[Note]) -> list[Note]:
    """Rút ra MỘT dòng giai điệu từ danh sách nốt đa âm bằng heuristic "skyline":
    khi hai nốt chồng lấn thời gian, giữ nốt có cao độ cao hơn cho đoạn giao nhau.

    QUAN TRỌNG: đây là một track **dẫn xuất** (derived) — không được gọi hàm này
    trên dữ liệu sẽ dùng làm "full polyphonic" track. Input `notes` không bị mutate;
    hàm trả về danh sách Note mới (dùng `Note.with_target_timing`/dataclasses.replace
    khi cần cắt ngắn, không sửa trực tiếp note gốc).
    """
    from dataclasses import replace

    notes_sorted = sorted(notes, key=lambda n: n.original.onset_seconds)
    melody: list[Note] = []

    for note in notes_sorted:
        if note.pitch_midi < settings.MELODY_MIN_MIDI_PITCH:
            # Nốt quá trầm hiếm khi là giai điệu chính — chỉ loại khỏi track MELODY
            # dẫn xuất này, không ảnh hưởng gì đến full polyphonic track.
            continue

        if not melody:
            melody.append(note)
            continue

        last = melody[-1]
        if note.original.onset_seconds >= last.original.offset_seconds:
            melody.append(note)
            continue

        if note.pitch_midi >= last.pitch_midi:
            if note.original.onset_seconds - last.original.onset_seconds >= _MIN_RESIDUAL_SECONDS:
                melody[-1] = replace(
                    last, original=replace(last.original, offset_seconds=note.original.onset_seconds)
                )
                melody.append(note)
            else:
                melody[-1] = note
        else:
            if note.original.offset_seconds - last.original.offset_seconds >= _MIN_RESIDUAL_SECONDS:
                trimmed = replace(
                    note, original=replace(note.original, onset_seconds=last.original.offset_seconds)
                )
                melody.append(trimmed)
            # else: note nằm hoàn toàn trong last -> bỏ qua khỏi track melody

    return melody
