from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.utils.ffmpeg_check import ffmpeg_available, ffprobe_available

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ffmpeg_found=ffmpeg_available(), ffprobe_found=ffprobe_available())
