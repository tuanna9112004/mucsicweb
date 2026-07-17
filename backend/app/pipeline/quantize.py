from dataclasses import replace

from app.music.note_models import Note

# "T" = triplet (bộ ba). 1/8 triplet = 1/3 beat, 1/16 triplet = 1/6 beat.
QUANTIZE_UNITS_BEATS: dict[str, float | None] = {
    "none": None,
    "1/4": 1.0,
    "1/8": 0.5,
    "1/16": 0.25,
    "1/8T": 1.0 / 3,
    "1/16T": 1.0 / 6,
}


def quantize_notes(notes: list[Note], unit_beats: float | None) -> list[Note]:
    """Snap onset/duration của mỗi nốt về lưới `unit_beats`, ĐỘC LẬP cho từng nốt.

    Không dedupe, không trim chồng lấn — nhiều nốt cùng lúc (hợp âm) hoặc nốt
    chồng thời gian là bình thường với dữ liệu đa âm và phải được giữ nguyên.
    Trả về Note MỚI (không mutate note đầu vào) — `onset_beat_raw`/`duration_beats_raw`
    giữ nguyên, chỉ `onset_beat_quantized`/`duration_beats_quantized`/`quantized` thay đổi.
    """
    if unit_beats is None:
        return [
            replace(
                note,
                onset_beat_quantized=note.onset_beat_raw,
                duration_beats_quantized=note.duration_beats_raw,
                quantized=False,
            )
            for note in notes
        ]

    result = []
    for note in notes:
        snapped_onset = round(note.onset_beat_raw / unit_beats) * unit_beats
        snapped_offset = round((note.onset_beat_raw + note.duration_beats_raw) / unit_beats) * unit_beats
        duration = max(unit_beats, snapped_offset - snapped_onset)
        result.append(
            replace(
                note,
                onset_beat_quantized=snapped_onset,
                duration_beats_quantized=duration,
                quantized=True,
            )
        )
    return result


def resolve_monophonic_overlaps(notes: list[Note], unit_beats: float | None) -> list[Note]:
    """Chỉ dùng cho track ĐƠN ÂM (melody đã qua skyline) sau khi quantize: quantize
    có thể khiến 2 nốt vốn tách biệt snap về cùng vị trí hoặc chồng lấn — với một
    dòng giai điệu đơn âm, đây là lỗi cần sửa (không thể có 2 nốt cùng lúc trong
    MỘT dòng giai điệu). KHÔNG áp dụng hàm này cho track đa âm/full piano.
    """
    if not notes:
        return []

    floor_duration = unit_beats if unit_beats else 0.0

    notes_sorted = sorted(notes, key=lambda n: n.onset_beat_quantized)

    deduped: list[Note] = []
    for note in notes_sorted:
        if deduped and note.onset_beat_quantized == deduped[-1].onset_beat_quantized:
            if note.model_amplitude > deduped[-1].model_amplitude:
                deduped[-1] = note
            continue
        deduped.append(note)

    result = list(deduped)
    for i in range(len(result) - 1):
        current = result[i]
        next_note = result[i + 1]
        current_end = current.onset_beat_quantized + current.duration_beats_quantized
        if current_end > next_note.onset_beat_quantized:
            new_duration = max(floor_duration, next_note.onset_beat_quantized - current.onset_beat_quantized)
            if new_duration <= 0:
                new_duration = next_note.onset_beat_quantized - current.onset_beat_quantized
            result[i] = replace(current, duration_beats_quantized=new_duration)

    return result
