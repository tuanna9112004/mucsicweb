from dataclasses import replace

from app.config import settings
from app.core.errors import NoMelodyDetectedError
from app.music.note_models import Note, OriginalTiming


def _merge_adjacent_same_pitch(
    notes: list[Note], merge_gap_ms: float, max_duration_ratio: float
) -> list[Note]:
    if not notes:
        return []

    merge_gap_seconds = merge_gap_ms / 1000.0
    notes_sorted = sorted(notes, key=lambda n: n.original.onset_seconds)
    merged: list[Note] = [notes_sorted[0]]

    for note in notes_sorted[1:]:
        last = merged[-1]
        gap_seconds = note.original.onset_seconds - last.original.offset_seconds

        longer = max(last.original.duration_seconds, note.original.duration_seconds)
        shorter = min(last.original.duration_seconds, note.original.duration_seconds)
        duration_ratio = shorter / longer if longer > 0 else 1.0

        # Basic Pitch chỉ tạo note event mới khi onset activation vượt ngưỡng tin
        # cậy — hai nốt cùng cao độ đứng sát nhau (dù gap=0) thường là hai lần
        # đánh nốt thật (vd nốt lặp lại), không phải một nốt bị vỡ do nhiễu. Chỉ
        # gộp khi một nốt ngắn bất thường so với nốt kia.
        should_merge = (
            note.pitch_midi == last.pitch_midi
            and gap_seconds <= merge_gap_seconds
            and duration_ratio < max_duration_ratio
        )

        if should_merge:
            total_duration = last.original.duration_seconds + note.original.duration_seconds
            if total_duration > 0:
                new_amplitude = (
                    last.model_amplitude * last.original.duration_seconds
                    + note.model_amplitude * note.original.duration_seconds
                ) / total_duration
            else:
                new_amplitude = last.model_amplitude
            merged[-1] = replace(
                last,
                original=OriginalTiming(
                    onset_seconds=last.original.onset_seconds, offset_seconds=note.original.offset_seconds
                ),
                model_amplitude=new_amplitude,
                merged=True,
            )
        else:
            merged.append(note)

    return merged


def clean_notes(
    notes: list[Note],
    merge_gap_ms: float | None = None,
    max_merge_duration_ratio: float | None = None,
    min_duration_ms: float | None = None,
    min_confidence: float | None = None,
) -> list[Note]:
    """Gộp các nốt liền kề cùng cao độ, sau đó loại nốt quá ngắn hoặc model_amplitude
    thấp. CHỈ dùng cho track đơn âm (melody) — không áp dụng cho full polyphonic
    track, nơi nhiều nốt cùng onset (hợp âm) là dữ liệu hợp lệ cần giữ nguyên.

    Thứ tự merge-trước-filter-sau là chủ đích: một lần merge có thể "cứu" hai mảnh
    nốt quá ngắn thành một nốt đủ dài và hợp lệ. Không mutate note đầu vào.
    """
    merge_gap_ms = settings.MERGE_GAP_MS if merge_gap_ms is None else merge_gap_ms
    max_merge_duration_ratio = (
        settings.MERGE_MAX_DURATION_RATIO
        if max_merge_duration_ratio is None
        else max_merge_duration_ratio
    )
    min_duration_ms = settings.MIN_NOTE_DURATION_MS if min_duration_ms is None else min_duration_ms
    min_confidence = settings.MIN_NOTE_CONFIDENCE if min_confidence is None else min_confidence

    merged = _merge_adjacent_same_pitch(notes, merge_gap_ms, max_merge_duration_ratio)

    min_duration_seconds = min_duration_ms / 1000.0
    cleaned = [
        note
        for note in merged
        if note.original.duration_seconds >= min_duration_seconds
        and note.model_amplitude >= min_confidence
    ]

    if not cleaned:
        raise NoMelodyDetectedError(
            "Không phát hiện được giai điệu rõ ràng trong file âm thanh này."
        )

    return cleaned
