import sys

import uvicorn

from app.utils.ffmpeg_check import ffmpeg_available, ffprobe_available


def main() -> None:
    if not ffmpeg_available() or not ffprobe_available():
        print(
            "CẢNH BÁO: Không tìm thấy FFmpeg/ffprobe trên PATH. "
            "Vui lòng cài đặt FFmpeg rồi khởi động lại trước khi phân tích file.",
            file=sys.stderr,
        )

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
