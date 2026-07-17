from dataclasses import dataclass, field, replace

import librosa
import numpy as np

from app.core.errors import AnalysisError
from app.music.note_models import Note

_MIN_METER_CONFIDENCE = 0.15


@dataclass
class BpmCandidate:
    bpm: float
    score: float


@dataclass
class TempoBeatResult:
    detected_bpm: float
    beat_times: np.ndarray  # seconds, ascending
    bpm_candidates: list[BpmCandidate] = field(default_factory=list)
    downbeat_times: list[float] = field(default_factory=list)
    time_signature: str | None = None
    time_signature_confidence: float | None = None


def _bpm_candidates(onset_env: np.ndarray, sr: int, hop_length: int, primary_bpm: float) -> list[BpmCandidate]:
    """BPM chính + ứng viên half-time/double-time, điểm số theo độ mạnh tự tương
    quan (autocorrelation) của onset envelope tại chu kỳ tương ứng — không chỉ trả
    một BPM duy nhất, để tầng gọi có thể xử lý trường hợp model nhận nhầm nửa/gấp
    đôi nhịp thật.
    """
    if primary_bpm <= 0:
        return [BpmCandidate(bpm=primary_bpm, score=1.0)]

    autocorr = librosa.autocorrelate(onset_env, max_size=len(onset_env))
    frames_per_second = sr / hop_length
    max_lag = len(autocorr) - 1

    raw_candidates = [primary_bpm, primary_bpm / 2.0, primary_bpm * 2.0]
    scored: list[tuple[float, float]] = []
    for bpm in raw_candidates:
        if bpm <= 0:
            continue
        lag = frames_per_second * 60.0 / bpm
        lag_idx = int(round(lag))
        score = float(autocorr[lag_idx]) if 0 < lag_idx <= max_lag else 0.0
        scored.append((bpm, score))

    max_score = max((s for _, s in scored), default=1.0) or 1.0
    candidates = [BpmCandidate(bpm=round(b, 2), score=round(s / max_score, 3)) for b, s in scored]
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _estimate_downbeats_and_meter(
    onset_env: np.ndarray, sr: int, hop_length: int, beat_times: np.ndarray
) -> tuple[list[float], str | None, float | None]:
    """Heuristic đơn giản để ước lượng downbeat + time signature: thử nhóm beat
    theo chu kỳ 3 hoặc 4, chọn cách nhóm + pha (phase) có độ tương phản salience
    (onset strength) giữa beat đầu nhóm và các beat còn lại rõ nhất.

    KHÔNG gán cứng 4/4 — trả (None, None) khi độ tin cậy quá thấp để không khẳng
    định sai. Đây là best-effort, không phải downbeat tracker chuyên dụng (loại
    DBN như madmom).
    """
    if len(beat_times) < 8:
        return [], None, None

    onset_times = librosa.times_like(onset_env, sr=sr, hop_length=hop_length)
    beat_saliences = np.interp(beat_times, onset_times, onset_env)

    best_group_size = None
    best_phase = 0
    best_contrast = -1.0

    for group_size in (3, 4):
        for phase in range(group_size):
            downbeat_mask = np.zeros(len(beat_saliences), dtype=bool)
            downbeat_mask[phase::group_size] = True
            downbeat_saliences = beat_saliences[downbeat_mask]
            other_saliences = beat_saliences[~downbeat_mask]
            if len(downbeat_saliences) == 0 or len(other_saliences) == 0:
                continue
            contrast = float(downbeat_saliences.mean() - other_saliences.mean())
            if contrast > best_contrast:
                best_contrast = contrast
                best_group_size = group_size
                best_phase = phase

    if best_group_size is None:
        return [], None, None

    max_possible = float(beat_saliences.max()) or 1.0
    confidence = max(0.0, min(1.0, best_contrast / max_possible))

    if confidence < _MIN_METER_CONFIDENCE:
        return [], None, None

    downbeat_times = [float(t) for t in beat_times[best_phase::best_group_size]]
    time_signature = f"{best_group_size}/4"
    return downbeat_times, time_signature, round(confidence, 3)


def detect_tempo_and_beats(y: np.ndarray, sr: int) -> TempoBeatResult:
    hop_length = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

    if len(beat_times) < 2:
        raise AnalysisError(
            "Không xác định được nhịp (beat) ổn định trong file âm thanh này."
        )

    detected_bpm = float(np.median(60.0 / np.diff(beat_times)))
    bpm_candidates = _bpm_candidates(onset_env, sr, hop_length, detected_bpm)
    downbeat_times, time_signature, time_signature_confidence = _estimate_downbeats_and_meter(
        onset_env, sr, hop_length, beat_times
    )

    return TempoBeatResult(
        detected_bpm=detected_bpm,
        beat_times=beat_times,
        bpm_candidates=bpm_candidates,
        downbeat_times=downbeat_times,
        time_signature=time_signature,
        time_signature_confidence=time_signature_confidence,
    )


def _time_to_beat(time_seconds: float, beat_times: np.ndarray) -> float:
    n = len(beat_times)
    index = int(np.searchsorted(beat_times, time_seconds, side="right") - 1)
    index = max(0, min(index, n - 2))
    interval = beat_times[index + 1] - beat_times[index]
    if interval <= 0:
        return float(index)
    return index + (time_seconds - beat_times[index]) / interval


def map_notes_to_beat_grid(notes: list[Note], beat_times: np.ndarray) -> list[Note]:
    """Gán onset_beat_raw/duration_beats_raw cho từng nốt bằng nội suy/ngoại suy
    tuyến tính theo beat_times đã phát hiện, rồi dịch toàn bộ nốt nếu nốt sớm nhất
    rơi vào beat âm (ngoại suy trước beat đầu tiên) để mọi thời điểm không âm.

    Trả về Note MỚI — không mutate note đầu vào, không đụng `note.original`.
    """
    mapped = []
    for note in notes:
        onset_beat = _time_to_beat(note.original.onset_seconds, beat_times)
        offset_beat = _time_to_beat(note.original.offset_seconds, beat_times)
        mapped.append(replace(note, onset_beat_raw=onset_beat, duration_beats_raw=offset_beat - onset_beat))

    if mapped:
        min_onset_beat = min(n.onset_beat_raw for n in mapped)
        if min_onset_beat < 0:
            mapped = [replace(n, onset_beat_raw=n.onset_beat_raw - min_onset_beat) for n in mapped]

    return mapped
