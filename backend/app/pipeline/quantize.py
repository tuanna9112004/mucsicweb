from app.pipeline.note_models import Note


def quantize_notes(notes: list[Note], unit_beats: float | None) -> list[Note]:
    """Snap start/end của mỗi nốt về lưới `unit_beats` (đơn vị: beat), rồi trim chồng lấn.

    `unit_beats=None` nghĩa là "không quantize" — copy nguyên giá trị raw sang các
    trường start_beat/duration_beats, đánh dấu quantized=False.
    """
    if unit_beats is None:
        for note in notes:
            note.start_beat = note.start_beat_raw
            note.duration_beats = note.duration_beats_raw
            note.quantized = False
        return notes

    for note in notes:
        snapped_start = round(note.start_beat_raw / unit_beats) * unit_beats
        snapped_end = round((note.start_beat_raw + note.duration_beats_raw) / unit_beats) * unit_beats
        note.start_beat = snapped_start
        note.duration_beats = max(unit_beats, snapped_end - snapped_start)
        note.quantized = True

    notes_sorted = sorted(notes, key=lambda n: n.start_beat)

    # Nhiều nốt riêng biệt có thể snap về đúng cùng một start_beat (đặc biệt với audio
    # đa âm phức tạp) — chỉ trim duration không đủ để đảm bảo đơn âm trong trường hợp
    # này, cần loại bớt hẳn, giữ lại nốt có confidence cao hơn.
    deduped: list[Note] = []
    for note in notes_sorted:
        if deduped and note.start_beat == deduped[-1].start_beat:
            if note.confidence > deduped[-1].confidence:
                deduped[-1] = note
            continue
        deduped.append(note)

    for i in range(len(deduped) - 1):
        current = deduped[i]
        next_note = deduped[i + 1]
        current_end = current.start_beat + current.duration_beats
        if current_end > next_note.start_beat:
            current.duration_beats = max(unit_beats, next_note.start_beat - current.start_beat)

    return deduped
