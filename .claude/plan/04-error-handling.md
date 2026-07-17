# Xử lý lỗi — 11 trường hợp bắt buộc (mục 7.8 spec)

Hierarchy trong `backend/app/core/errors.py`:
```python
class PipelineError(Exception):
    code: str
    http_status: int
    user_message: str
```
+ `@app.exception_handler(PipelineError)` trả `{"error": {"code", "message"}}`.
+ Catch-all `@app.exception_handler(Exception)` log full traceback **server-side only**, trả 500 tổng quát đã sanitize — **không bao giờ hiển thị stack trace ra client**.

Thứ tự ingestion (rẻ → đắt): kiểm tra extension → đếm byte khi stream (chặn sớm) → ffprobe probe (gộp luôn unreadable/wrong-format/too-long) → normalization. Chỉ chạy bước đắt tiền khi bước rẻ đã pass.

| # | Trường hợp lỗi | Nơi phát hiện | Code / HTTP |
|---|---|---|---|
| 1 | Chưa chọn file | Client chặn submit; server reject phần multipart rỗng | `NO_FILE_SELECTED` / 400 |
| 2 | Sai định dạng | ffprobe kiểm tra codec/container (tin ffprobe hơn phần mở rộng file) | `UNSUPPORTED_FORMAT` / 415 |
| 3 | File không đọc được | ffprobe parse thất bại | `FILE_UNREADABLE` / 422 |
| 4 | File quá lớn (>30MB) | Kiểm tra `Content-Length` + đếm byte khi stream (abort giữa chừng) | `FILE_TOO_LARGE` / 413 |
| 5 | File quá dài (>90s) | ffprobe duration, fail fast trước normalization | `FILE_TOO_LONG` / 422 |
| 6 | Không tìm thấy FFmpeg | Check lúc khởi động + `/api/health` + lazy re-check lúc ingest | `FFMPEG_NOT_FOUND` / 503 |
| 7 | Không phát hiện melody rõ ràng | `note_cleanup.py` — danh sách rỗng sau lọc, hoặc 0 nốt thô từ Basic Pitch | `NO_MELODY_DETECTED` / 422 |
| 8 | Thư viện phân tích bị lỗi | try/except quanh gọi librosa/basic-pitch | `ANALYSIS_ERROR` / 500 |
| 9 | Không tạo được MIDI | try/except quanh `pretty_midi` write | `MIDI_EXPORT_FAILED` / 500 |
| 10 | Không đủ bộ nhớ | Giới hạn 30MB/90s là phòng ngừa chính; bắt `MemoryError` ở biên pipeline runner. **Giới hạn đã biết**: OOM native thật trên Windows có thể crash hẳn uvicorn worker thay vì raise exception sạch — đã ghi nhận, không hứa hẹn quá mức | `OUT_OF_MEMORY` / 507 |
| 11 | Tác vụ bị hủy | Cờ cooperative kiểm tra giữa các stage (không ngắt giữa lúc basic-pitch đang infer) | `TASK_CANCELLED`, thể hiện qua job status, không phải lỗi HTTP trên chính `/cancel` |

## Mã lỗi bổ sung ngoài 11 trường hợp gốc (phát hiện khi implement Stage 4/6)

Ngoài 11 lỗi bắt buộc trong spec, tầng job/API cần thêm các lỗi vòng đời job — nếu không, các endpoint `analyze`/`notes`/`cancel`/`download/*` sẽ phải dùng `HTTPException` mặc định của FastAPI (`{"detail": "..."}`), **không khớp** format `{"error": {"code","message"}}` mà frontend `errors.js` cần để hiển thị thông báo đúng (đã phát hiện đây là bug thực tế khi review lại `app.js`, xem [`06-roadmap.md`](06-roadmap.md) Stage 6). Đã thêm vào `core/errors.py` và dùng nhất quán trong mọi route thay vì `HTTPException` trực tiếp:

| Code | HTTP | Ý nghĩa |
|---|---|---|
| `JOB_NOT_FOUND` | 404 | job_id không tồn tại trong job_store (vd server đã restart, mất state in-memory) |
| `JOB_ALREADY_RUNNING` | 409 | Gọi `/analyze` khi job đang ở trạng thái RUNNING |
| `JOB_RESULT_NOT_READY` | 409 | Gọi `/notes` hoặc `/download/*` trước khi job hoàn tất phân tích |

## Nguyên tắc thông báo cho người dùng (mục 7.8/7.9 spec)

- Mọi thông báo lỗi phải giải thích ngắn gọn nguyên nhân + hướng xử lý (vd: "Không tìm thấy FFmpeg — vui lòng cài đặt FFmpeg và khởi động lại ứng dụng").
- `frontend/js/errors.js` map `code` → message hiển thị, tách biệt hoàn toàn với message kỹ thuật server log.
