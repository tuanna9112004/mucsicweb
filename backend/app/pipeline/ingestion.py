import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.errors import (
    FFmpegNotFoundError,
    FileTooLargeError,
    FileTooLongError,
    FileUnreadableError,
    UnsupportedFormatError,
)

_STREAM_CHUNK_BYTES = 1024 * 1024
_PROBE_TIMEOUT_SECONDS = 30


@dataclass
class AudioProbeInfo:
    duration_seconds: float
    format_name: str


def validate_extension(filename: str, allowed_extensions: tuple[str, ...]) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        raise UnsupportedFormatError(
            f"Định dạng file '{ext or '(không có phần mở rộng)'}' không được hỗ trợ. "
            f"Chỉ chấp nhận: {', '.join(allowed_extensions)}."
        )


def save_upload(file_stream: BinaryIO, dest_path: Path, max_bytes: int) -> int:
    """Stream-copy file_stream to dest_path, aborting if max_bytes is exceeded.

    Returns the total number of bytes written. Cleans up the partial file on failure.
    """
    total_bytes = 0
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = file_stream.read(_STREAM_CHUNK_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise FileTooLargeError(
                        f"File vượt quá dung lượng tối đa {max_bytes // (1024 * 1024)}MB."
                    )
                out.write(chunk)
    except FileTooLargeError:
        dest_path.unlink(missing_ok=True)
        raise
    return total_bytes


def probe_audio(path: Path) -> AudioProbeInfo:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise FFmpegNotFoundError(
            "Không tìm thấy FFmpeg/ffprobe trên máy. Vui lòng cài đặt FFmpeg và khởi động lại ứng dụng."
        )

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration,format_name",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise FileUnreadableError("Hết thời gian chờ khi đọc file âm thanh.") from exc

    if result.returncode != 0 or not result.stdout.strip():
        raise FileUnreadableError(
            "Không thể đọc file âm thanh. File có thể bị hỏng hoặc không phải định dạng âm thanh hợp lệ."
        )

    try:
        data = json.loads(result.stdout)
        fmt = data["format"]
        duration_seconds = float(fmt["duration"])
        format_name = fmt.get("format_name", "")
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise FileUnreadableError("Không đọc được thông tin định dạng của file âm thanh.") from exc

    return AudioProbeInfo(duration_seconds=duration_seconds, format_name=format_name)


def validate_duration(duration_seconds: float, max_seconds: float) -> None:
    if duration_seconds > max_seconds:
        raise FileTooLongError(
            f"Thời lượng file ({duration_seconds:.1f}s) vượt quá giới hạn tối đa {max_seconds:.0f}s."
        )
