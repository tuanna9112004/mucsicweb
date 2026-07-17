import logging
from pathlib import Path

from app.core.errors import AnalysisError
from app.music.note_models import Note, OriginalTiming, PedalEvent
from app.transcribers.base import BaseTranscriber, TranscriptionResult

logger = logging.getLogger(__name__)

_CHECKPOINT_PATH = Path.home() / "piano_transcription_inference_data" / "note_F1=0.9677_pedal_F1=0.9186.pth"
_CHECKPOINT_MIN_SIZE_BYTES = int(1.6e8)


class PianoTranscriber(BaseTranscriber):
    """Model piano chuyên dụng (ByteDance/Kong et al. `piano_transcription_inference`)
    — nhận diện polyphonic note onset/offset/velocity và sustain pedal.

    Cài đặt:
        pip install torch --index-url https://download.pytorch.org/whl/cpu
        pip install piano_transcription_inference torchlibrosa matplotlib

    Checkpoint (~164MB) KHÔNG tự tải được trên Windows (package gọi `os.system("wget ...")`,
    Windows không có wget thật). Tải thủ công:
        curl.exe -L -o "%USERPROFILE%\\piano_transcription_inference_data\\note_F1=0.9677_pedal_F1=0.9186.pth" ^
            "https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1"
    """

    name = "piano_cnn"

    def __init__(self) -> None:
        self._model = None

    def is_available(self) -> bool:
        try:
            import torch  # noqa: F401
            from piano_transcription_inference import PianoTranscription  # noqa: F401
        except ImportError:
            return False

        return _CHECKPOINT_PATH.exists() and _CHECKPOINT_PATH.stat().st_size > _CHECKPOINT_MIN_SIZE_BYTES

    def _get_model(self):
        if self._model is None:
            from piano_transcription_inference import PianoTranscription

            self._model = PianoTranscription(device="cpu", checkpoint_path=str(_CHECKPOINT_PATH))
        return self._model

    def transcribe(self, audio_path: Path, work_dir: Path) -> TranscriptionResult:
        import librosa
        from piano_transcription_inference import sample_rate as pt_sample_rate

        try:
            audio, _ = librosa.load(str(audio_path), sr=pt_sample_rate, mono=True)
            model = self._get_model()
            scratch_midi_path = work_dir / "_piano_cnn_raw.mid"
            result = model.transcribe(audio, str(scratch_midi_path))
        except Exception as exc:
            raise AnalysisError(
                "Model piano chuyên dụng gặp lỗi khi phân tích file này."
            ) from exc

        notes = []
        for ev in result.get("est_note_events", []):
            velocity = int(min(max(round(ev["velocity"]), 1), 127))
            notes.append(
                Note(
                    pitch_midi=int(ev["midi_note"]),
                    original=OriginalTiming(
                        onset_seconds=float(ev["onset_time"]), offset_seconds=float(ev["offset_time"])
                    ),
                    model_amplitude=velocity / 127.0,
                    velocity_estimate=velocity,
                    source_model=self.name,
                )
            )

        pedal_events = [
            PedalEvent(onset_seconds=float(ev["onset_time"]), offset_seconds=float(ev["offset_time"]))
            for ev in result.get("est_pedal_events", [])
        ]

        return TranscriptionResult(notes=notes, pedal_events=pedal_events)
