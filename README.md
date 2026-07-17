# Melody Tempo Analyzer

Web app chạy hoàn toàn local: nhận file MP3/WAV, tự động phát hiện tempo/beat, tách giai điệu chính, chuyển thành nốt MIDI đã căn nhịp, cho phép đổi sang tempo đích 135–140 BPM (giữ nguyên cao độ), xuất ra file `.mid` + `.json`.

Xem [`CLAUDE.md`](CLAUDE.md) và [`.claude/plan/`](.claude/plan/) để biết chi tiết kiến trúc, thuật toán, và tiến độ triển khai.

## Yêu cầu môi trường

- **Python 3.10** (khuyến nghị dùng bản cài từ python.org, không dùng Python từ Microsoft Store — bản Store thiếu tương thích với một số gói).
- **FFmpeg** (bao gồm `ffmpeg` và `ffprobe`) phải có trên PATH.

Cài nhanh trên Windows bằng winget:

```powershell
winget install --id Python.Python.3.10 -e
winget install --id Gyan.FFmpeg -e
```

Mở **terminal mới** sau khi cài để PATH được cập nhật, rồi xác nhận:

```powershell
python --version
ffmpeg -version
ffprobe -version
```

Nếu `python` vẫn báo lỗi (bị Windows Store alias che), vào **Settings → Apps → Advanced app settings → App execution aliases** và tắt `python.exe`/`python3.exe`, hoặc gọi trực tiếp bằng đường dẫn đầy đủ tới bản cài thật.

## Cài đặt

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

## Chạy ứng dụng

```powershell
cd backend
.venv\Scripts\python.exe run_server.py
```

Server chạy tại `http://127.0.0.1:8000` — mở địa chỉ này bằng trình duyệt. Giao diện web (`frontend/`) được phục vụ trực tiếp bởi server, không cần bước build riêng.

Nếu console in cảnh báo thiếu FFmpeg, hãy cài đặt FFmpeg (xem trên) rồi khởi động lại server.

## Chạy test

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v
```

Bỏ qua các test tích hợp chậm (cần chạy Basic Pitch thật):

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v -m "not slow"
```

## File mẫu để thử nghiệm

- `samples/jtwayne-pianos-by-jtwayne-7-174717.mp3` — piano đơn, ~19 giây, dùng để thử nghiệm thủ công toàn bộ luồng qua giao diện web.
- `samples/farran_ez-minimal-piano-underscore-456148.mp3` — piano hòa âm dày (chords + bass giữ dài), ~26 giây, dùng để kiểm tra khả năng lọc nốt bass khỏi giai điệu chính (`MELODY_MIN_MIDI_PITCH`).
- `backend/tests/fixtures/synth_melody_120bpm.wav` — giai điệu tổng hợp (sinh bằng `backend/tests/fixtures/generate_fixture.py`), dùng cho test tự động, có ground-truth biết trước (8 nốt, 120 BPM).
- `backend/scripts/debug_pipeline.py` — chạy pipeline phân tích trực tiếp qua CLI (không qua web UI), hữu ích để debug nhanh:
  ```powershell
  .venv\Scripts\python.exe scripts\debug_pipeline.py ..\samples\jtwayne-pianos-by-jtwayne-7-174717.mp3 --target-bpm 138 --quantize 1/8
  ```

## Giới hạn đã biết (MVP)

- Chỉ xử lý một tác vụ tại một thời điểm (không có hàng đợi).
- Trạng thái job lưu trong bộ nhớ — khởi động lại server sẽ mất job đang có, cần tải file lên lại.
- Giới hạn đầu vào: MP3/WAV, tối đa 30MB, tối đa 90 giây.
- Không tách đa nhạc cụ thành nhiều track MIDI — chỉ trích xuất một dòng giai điệu chính (heuristic "skyline": ưu tiên nốt cao độ cao hơn khi có chồng lấn).
- Không đảm bảo chính xác 100% với mọi loại bài hát — xem `.claude/plan/00-product-spec.md` mục "nhóm đầu vào cho kết quả tốt/kém hơn".
