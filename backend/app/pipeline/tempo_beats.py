from dataclasses import dataclass

import librosa
import numpy as np

from app.core.errors import AnalysisError
from app.pipeline.note_models import Note


@dataclass
class TempoBeatResult:
    detected_bpm: float
    beat_times: np.ndarray  # seconds, ascending


def detect_tempo_and_beats(y: np.ndarray, sr: int) -> TempoBeatResult:
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(beat_times) < 2:
        raise AnalysisError(
            "Không xác định được nhịp (beat) ổn định trong file âm thanh này."
        )

    detected_bpm = float(np.median(60.0 / np.diff(beat_times)))
    return TempoBeatResult(detected_bpm=detected_bpm, beat_times=beat_times)


def _time_to_beat(time_seconds: float, beat_times: np.ndarray) -> float:
    n = len(beat_times)
    index = int(np.searchsorted(beat_times, time_seconds, side="right") - 1)
    index = max(0, min(index, n - 2))
    interval = beat_times[index + 1] - beat_times[index]
    if interval <= 0:
        return float(index)
    return index + (time_seconds - beat_times[index]) / interval


def map_notes_to_beat_grid(notes: list[Note], beat_times: np.ndarray) -> list[Note]:
    """Gán start_beat_raw/duration_beats_raw cho từng nốt bằng nội suy/ngoại suy tuyến
    tính theo beat_times đã phát hiện, rồi dịch toàn bộ nốt nếu nốt sớm nhất rơi vào
    beat âm (ngoại suy trước beat đầu tiên) để đảm bảo mọi thời điểm xuất ra không âm.
    """
    for note in notes:
        start_beat = _time_to_beat(note.start_time_seconds, beat_times)
        end_beat = _time_to_beat(note.end_time_seconds, beat_times)
        note.start_beat_raw = start_beat
        note.duration_beats_raw = end_beat - start_beat
        note.start_beat = start_beat
        note.duration_beats = note.duration_beats_raw

    if notes:
        min_start_beat = min(note.start_beat_raw for note in notes)
        if min_start_beat < 0:
            for note in notes:
                note.start_beat_raw -= min_start_beat
                note.start_beat -= min_start_beat

    return notes
