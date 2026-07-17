# Melody Tempo Analyzer

Web app chạy hoàn toàn local: nhận file MP3/WAV, tự động phát hiện tempo/beat, tách giai điệu chính, chuyển thành nốt MIDI đã căn nhịp, cho phép đổi sang tempo đích 135–140 BPM (giữ nguyên cao độ), xuất ra file `.mid` + `.json`.

Không phải phần mềm sáng tác nhạc — đây là hệ thống **phân tích và chuyển đổi** âm thanh có sẵn thành dữ liệu nốt có thể tái sử dụng trong DAW.

## Tài liệu chi tiết

Toàn bộ đặc tả sản phẩm và kế hoạch triển khai đầy đủ nằm trong `.claude/plan/`:

- [`00-product-spec.md`](.claude/plan/00-product-spec.md) — mục tiêu, bài toán thực tế, phạm vi MVP (in/out of scope)
- [`01-architecture.md`](.claude/plan/01-architecture.md) — cấu trúc thư mục, stack, thư viện & version, gotcha trên Windows
- [`02-algorithms.md`](.claude/plan/02-algorithms.md) — thuật toán lõi: beat-mapping, note cleanup, quantize, retiming, key estimation (kèm threshold số cụ thể)
- [`03-api-schemas.md`](.claude/plan/03-api-schemas.md) — API endpoints, Pydantic schemas, ví dụ JSON output
- [`04-error-handling.md`](.claude/plan/04-error-handling.md) — bảng ánh xạ 11 trường hợp lỗi → mã lỗi/HTTP status
- [`05-testing.md`](.claude/plan/05-testing.md) — chiến lược test, cách tạo fixture âm thanh tổng hợp
- [`06-roadmap.md`](.claude/plan/06-roadmap.md) — **tiến độ theo giai đoạn (checklist sống, cập nhật khi hoàn thành mỗi stage)**

Khi cần chi tiết về một phần cụ thể, đọc file tương ứng thay vì suy đoán lại từ đầu.

## Quyết định kỹ thuật đã chốt (không re-litigate)

- **Backend**: Python 3.10 + FastAPI (đã cài qua winget). Không dùng Python từ Microsoft Store alias.
- **Melody → MIDI**: Basic Pitch (Spotify, chạy local qua ONNX Runtime trên Windows — không cài extra `[tf]`).
- **Tempo/beat detection**: librosa (`librosa.beat.beat_track`).
- **Giao diện**: local web server (FastAPI/uvicorn) mở bằng trình duyệt tại `http://localhost:PORT`. Không phải Electron.
- **Frontend**: HTML/CSS/JS thuần (ES modules, không build step), phục vụ qua `FastAPI StaticFiles`. Không dùng React/Node build toolchain.
- **MIDI export**: `pretty_midi`.
- **Đổi tempo giữ nguyên cao độ**: vì output là MIDI (không phải audio), việc này chỉ là tính lại timestamp theo beat — **không cần time-stretch audio** (pyrubberband...) cho MVP. Time-stretch chỉ cần cho tính năng phụ "nghe thử audio" (ngoài phạm vi MVP core).
- **Job model**: một job hiện tại duy nhất trong bộ nhớ (không queue, không xử lý đồng thời — đúng phạm vi MVP).

## Môi trường máy hiện tại

- Python 3.10.11 và FFmpeg 8.1.2 đã được cài qua `winget` (2026-07-17). Nếu venv/dependency có vấn đề, kiểm tra lại bằng `python --version` và `ffmpeg -version` trong terminal mới trước khi debug sâu hơn.
- Git repo được khởi tạo tại thư mục gốc dự án.
- Node v24 có sẵn trên máy nhưng **không dùng cho dự án này** (frontend là vanilla JS, không cần npm).

## Quy ước code

- Threshold số (MIN_NOTE_DURATION_MS, MERGE_GAP_MS, MIN_NOTE_CONFIDENCE, v.v.) tập trung tại `backend/app/config.py` — xem giá trị cụ thể trong [`02-algorithms.md`](.claude/plan/02-algorithms.md), không hardcode rải rác.
- Tên trường JSON output phải khớp chính xác với ví dụ trong [`03-api-schemas.md`](.claude/plan/03-api-schemas.md) (đã đối chiếu với 2 ví dụ JSON gốc trong đặc tả sản phẩm).
- Không viết stack trace ra response cho client — xem [`04-error-handling.md`](.claude/plan/04-error-handling.md).
