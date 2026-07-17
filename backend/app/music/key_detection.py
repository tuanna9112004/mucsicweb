from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.music.note_models import Note

_PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Kessler key profiles (thực nghiệm âm nhạc học, chuẩn phổ biến nhất
# cho key-finding bằng tương quan pitch-class).
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

_MIN_KEY_CONFIDENCE = 0.15


@dataclass
class KeyEstimate:
    key_name: str  # vd "C Major"
    relative_key_name: str  # vd "A Minor"
    confidence: float


def _pitch_class_histogram(notes: list[Note]) -> np.ndarray:
    histogram = np.zeros(12)
    for note in notes:
        histogram[note.pitch_midi % 12] += note.original.duration_seconds
    total = histogram.sum()
    if total > 0:
        histogram /= total
    return histogram


def _correlate(histogram: np.ndarray, profile: np.ndarray, root: int) -> float:
    rotated_profile = np.roll(profile, root)
    if np.std(histogram) == 0 or np.std(rotated_profile) == 0:
        return 0.0
    return float(np.corrcoef(histogram, rotated_profile)[0, 1])


def detect_key(notes: list[Note]) -> Optional[KeyEstimate]:
    """Ước lượng tông bằng thuật toán Krumhansl-Schmukler: tương quan phân bố
    pitch-class (trọng số theo thời lượng) với 24 profile major/minor đã biết.

    Trả về None nếu độ tin cậy quá thấp — không khẳng định tông khi dữ liệu
    không đủ rõ ràng.
    """
    if not notes:
        return None

    histogram = _pitch_class_histogram(notes)

    best_score = -2.0
    best_root = 0
    best_is_major = True

    for root in range(12):
        major_score = _correlate(histogram, _MAJOR_PROFILE, root)
        minor_score = _correlate(histogram, _MINOR_PROFILE, root)

        if major_score > best_score:
            best_score = major_score
            best_root = root
            best_is_major = True
        if minor_score > best_score:
            best_score = minor_score
            best_root = root
            best_is_major = False

    confidence = max(0.0, best_score)
    if confidence < _MIN_KEY_CONFIDENCE:
        return None

    root_name = _PITCH_CLASS_NAMES[best_root]
    if best_is_major:
        key_name = f"{root_name} Major"
        relative_root = (best_root + 9) % 12
        relative_key_name = f"{_PITCH_CLASS_NAMES[relative_root]} Minor"
    else:
        key_name = f"{root_name} Minor"
        relative_root = (best_root + 3) % 12
        relative_key_name = f"{_PITCH_CLASS_NAMES[relative_root]} Major"

    return KeyEstimate(key_name=key_name, relative_key_name=relative_key_name, confidence=confidence)
