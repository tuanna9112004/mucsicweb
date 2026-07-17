from typing import Optional

import numpy as np

from app.music.note_models import ChordSpan, Note

_PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# (nhãn hậu tố, các quãng tính từ root theo nửa cung)
_CHORD_TEMPLATES: list[tuple[str, tuple[int, ...]]] = [
    ("", (0, 4, 7)),  # major
    ("m", (0, 3, 7)),  # minor
    ("dim", (0, 3, 6)),  # diminished
    ("aug", (0, 4, 8)),  # augmented
    ("sus2", (0, 2, 7)),
    ("sus4", (0, 5, 7)),
    ("7", (0, 4, 7, 10)),  # dominant 7
    ("maj7", (0, 4, 7, 11)),
    ("m7", (0, 3, 7, 10)),
]

_MIN_CHORD_SCORE = 0.35
_FALLBACK_WINDOW_SECONDS = 1.0
_NO_CHORD_SYMBOL = "N"


def _active_notes_in_window(notes: list[Note], start: float, end: float) -> list[Note]:
    return [n for n in notes if n.original.onset_seconds < end and n.original.offset_seconds > start]


def _pitch_class_weights(notes: list[Note], start: float, end: float) -> np.ndarray:
    weights = np.zeros(12)
    for note in notes:
        overlap = min(note.original.offset_seconds, end) - max(note.original.onset_seconds, start)
        if overlap > 0:
            weights[note.pitch_midi % 12] += overlap
    return weights


def _best_chord_label(weights: np.ndarray) -> tuple[Optional[str], Optional[int], float]:
    total_weight = weights.sum()
    if total_weight <= 0:
        return None, None, 0.0

    best_score = -1.0
    best_root = 0
    best_suffix = ""

    for root in range(12):
        for suffix, intervals in _CHORD_TEMPLATES:
            template_pcs = [(root + interval) % 12 for interval in intervals]
            weight_in_template = sum(weights[pc] for pc in template_pcs)
            n_present = sum(1 for pc in template_pcs if weights[pc] > 0)
            recall = n_present / len(template_pcs)
            precision = weight_in_template / total_weight if total_weight > 0 else 0.0
            score = recall * precision
            if score > best_score:
                best_score = score
                best_root = root
                best_suffix = suffix

    return best_suffix, best_root, best_score


def _window_boundaries(notes: list[Note], beat_times: "np.ndarray | None") -> list[tuple[float, float]]:
    if beat_times is not None and len(beat_times) >= 2:
        return [(float(beat_times[i]), float(beat_times[i + 1])) for i in range(len(beat_times) - 1)]

    if not notes:
        return []
    end_time = max(n.original.offset_seconds for n in notes)
    boundaries = []
    t = 0.0
    while t < end_time:
        boundaries.append((t, t + _FALLBACK_WINDOW_SECONDS))
        t += _FALLBACK_WINDOW_SECONDS
    return boundaries


def detect_chords(notes: list[Note], beat_times: "np.ndarray | None" = None) -> list[ChordSpan]:
    """Nhận diện hợp âm theo timeline bằng cách gộp nốt theo từng cửa sổ (mỗi beat
    nếu có beat_times, ngược lại cửa sổ 1 giây cố định), khớp pitch-class set với
    các mẫu hợp âm phổ biến (major/minor/dim/aug/sus2/sus4/7/maj7/m7).

    Các cửa sổ liên tiếp cho cùng một hợp âm được gộp lại thành một ChordSpan —
    tránh đổi hợp âm liên tục chỉ vì một nốt trang trí thoáng qua.
    """
    boundaries = _window_boundaries(notes, beat_times)
    if not boundaries:
        return []

    raw_spans: list[ChordSpan] = []
    for start, end in boundaries:
        active = _active_notes_in_window(notes, start, end)
        weights = _pitch_class_weights(active, start, end)
        suffix, root, score = _best_chord_label(weights)

        if root is None or score < _MIN_CHORD_SCORE:
            raw_spans.append(
                ChordSpan(
                    start_time_seconds=start,
                    end_time_seconds=end,
                    chord_symbol=_NO_CHORD_SYMBOL,
                    root=None,
                    bass=None,
                    pitch_classes=[],
                    confidence=0.0,
                )
            )
            continue

        root_name = _PITCH_CLASS_NAMES[root]
        bass_note = min(active, key=lambda n: n.pitch_midi) if active else None
        bass_name = _PITCH_CLASS_NAMES[bass_note.pitch_midi % 12] if bass_note else root_name

        symbol = f"{root_name}{suffix}"
        if bass_name != root_name:
            symbol = f"{symbol}/{bass_name}"

        template_intervals = dict(_CHORD_TEMPLATES)[suffix]
        pitch_classes = [_PITCH_CLASS_NAMES[(root + i) % 12] for i in template_intervals]

        raw_spans.append(
            ChordSpan(
                start_time_seconds=start,
                end_time_seconds=end,
                chord_symbol=symbol,
                root=root_name,
                bass=bass_name,
                pitch_classes=pitch_classes,
                confidence=min(1.0, score),
            )
        )

    return _merge_adjacent_same_chord(raw_spans)


def _merge_adjacent_same_chord(spans: list[ChordSpan]) -> list[ChordSpan]:
    if not spans:
        return []

    merged = [spans[0]]
    for span in spans[1:]:
        last = merged[-1]
        if span.chord_symbol == last.chord_symbol:
            last.end_time_seconds = span.end_time_seconds
            last.confidence = max(last.confidence, span.confidence)
        else:
            merged.append(span)

    return merged
