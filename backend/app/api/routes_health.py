from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.transcribers.piano_transcriber import PianoTranscriber
from app.utils.ffmpeg_check import ffmpeg_available, ffprobe_available

router = APIRouter()
_piano_transcriber = PianoTranscriber()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ffmpeg_found=ffmpeg_available(),
        ffprobe_found=ffprobe_available(),
        piano_model_available=_piano_transcriber.is_available(),
    )
