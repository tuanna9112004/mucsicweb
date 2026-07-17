import numpy as np

from app.music.note_models import Note


def _otsu_threshold(pitches: np.ndarray, weights: np.ndarray, min_pitch: int, max_pitch: int) -> int:
    """Tìm điểm chia (threshold) tối đa hóa phương sai giữa 2 cụm (Otsu's method),
    áp dụng trên phân bố cao độ (trọng số theo thời lượng nốt) — thay cho một
    ngưỡng cố định như G3 cho mọi bài.
    """
    best_threshold = min_pitch
    best_between_class_variance = -1.0
    total_weight = weights.sum()
    if total_weight <= 0:
        return min_pitch

    for t in range(min_pitch, max_pitch):
        low_mask = pitches <= t
        w0 = weights[low_mask].sum()
        w1 = total_weight - w0
        if w0 == 0 or w1 == 0:
            continue
        m0 = (pitches[low_mask] * weights[low_mask]).sum() / w0
        m1 = (pitches[~low_mask] * weights[~low_mask]).sum() / w1
        variance = w0 * w1 * (m0 - m1) ** 2
        if variance > best_between_class_variance:
            best_between_class_variance = variance
            best_threshold = t

    return best_threshold


def derive_bass_track(notes: list[Note]) -> list[Note]:
    """Rút ra track bass bằng ngưỡng cao độ tính THÍCH ỨNG theo phân bố cao độ của
    chính bài đó (Otsu threshold trên histogram cao độ có trọng số thời lượng),
    thay vì một ngưỡng cố định (vd G3) áp dụng cho mọi bài.

    Trả về [] nếu bài không có vùng trầm tách biệt rõ ràng (vd toàn bộ nốt nằm
    trong một dải cao độ hẹp) — không ép một "bass track" giả khi dữ liệu không
    hỗ trợ điều đó.
    """
    if not notes:
        return []

    pitches = np.array([n.pitch_midi for n in notes], dtype=np.float64)
    weights = np.array([max(n.original.duration_seconds, 0.01) for n in notes], dtype=np.float64)
    min_pitch, max_pitch = int(pitches.min()), int(pitches.max())

    if max_pitch - min_pitch < 4:
        return []  # dải cao độ quá hẹp, không có "vùng bass" tách biệt có ý nghĩa

    threshold = _otsu_threshold(pitches, weights, min_pitch, max_pitch)
    bass_notes = [note for note in notes if note.pitch_midi <= threshold]

    # Nếu ngưỡng Otsu chọn ra gần như toàn bộ nốt (bài không thực sự có 2 cụm
    # cao độ rõ ràng), coi như không có bass track riêng biệt.
    if len(bass_notes) >= len(notes) * 0.85:
        return []

    return sorted(bass_notes, key=lambda n: n.original.onset_seconds)
