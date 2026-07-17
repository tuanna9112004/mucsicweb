from dataclasses import dataclass

import librosa
import numpy as np


@dataclass
class TempoBeatResult:
    detected_bpm: float
    beat_times: np.ndarray  # seconds, ascending


def detect_tempo_and_beats(y: np.ndarray, sr: int) -> TempoBeatResult:
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(beat_times) >= 2:
        detected_bpm = float(np.median(60.0 / np.diff(beat_times)))
    else:
        detected_bpm = float(np.asarray(tempo).reshape(-1)[0])

    return TempoBeatResult(detected_bpm=detected_bpm, beat_times=beat_times)
