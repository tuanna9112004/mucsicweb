from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from app.core.errors import FileUnreadableError


def normalize_audio(source_path: Path, dest_path: Path, target_sr: int) -> np.ndarray:
    """Decode source_path to mono float32 audio at target_sr and write it as a PCM16 WAV to dest_path.

    Returns the loaded audio samples so callers (tempo/beat detection) can reuse them
    without re-decoding the file.
    """
    try:
        y, _ = librosa.load(str(source_path), sr=target_sr, mono=True)
    except Exception as exc:
        raise FileUnreadableError(
            "Không thể chuẩn hóa file âm thanh. File có thể bị hỏng hoặc không phải định dạng hợp lệ."
        ) from exc

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest_path), y, target_sr, subtype="PCM_16")
    return y
