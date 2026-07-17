# Melody Tempo Analyzer

Web app chạy hoàn toàn local, phân tích file MP3/WAV thành dữ liệu nốt MIDI có thể tái sử dụng trong DAW. Có 2 chế độ:

- **Piano Accurate** (mặc định) — model piano chuyên dụng (`piano_transcription_inference`, fallback Basic Pitch), giữ **toàn bộ nốt đa âm** (hợp âm, bass, pedal) làm nguồn dữ liệu chính, suy ra thêm track melody/bass, nhận diện hợp âm theo timeline và tông.
- **Melody Quick** — Basic Pitch, chỉ trích một dòng giai điệu đơn âm (`monophonic_melody`), nhanh hơn, không tính hợp âm/tông.

Không phải phần mềm sáng tác nhạc — đây là hệ thống **phân tích và chuyển đổi** âm thanh có sẵn.

## Tài liệu chi tiết

`.claude/plan/`:

- [`00-product-spec.md`](.claude/plan/00-product-spec.md) — đặc tả gốc (MVP v1, giai điệu đơn âm — **một phần đã lỗi thời sau v2**, xem file 07)
- [`01-architecture.md`](.claude/plan/01-architecture.md) — cấu trúc thư mục/stack **v1** (chưa cập nhật `music/`, `transcribers/` — đối chiếu code thật)
- [`02-algorithms.md`](.claude/plan/02-algorithms.md) — thuật toán v1 + các bug đã phát hiện/sửa (lọc bass, gộp nhầm nốt lặp) — vẫn đúng cho phần liên quan
- [`03-api-schemas.md`](.claude/plan/03-api-schemas.md) — schema **v1** (đã thay bằng schema v2, xem `api/schemas.py` + file 07)
- [`04-error-handling.md`](.claude/plan/04-error-handling.md) — bảng lỗi, vẫn đúng
- [`05-testing.md`](.claude/plan/05-testing.md) — chiến lược test v1, vẫn đúng nguyên tắc
- [`06-roadmap.md`](.claude/plan/06-roadmap.md) — **checklist tiến độ v1 (Stage 0-6), đã hoàn tất**
- [`07-v2-piano-accurate-upgrade.md`](.claude/plan/07-v2-piano-accurate-upgrade.md) — **BẮT ĐẦU TỪ ĐÂY cho trạng thái hiện tại**: toàn bộ nâng cấp v2, trạng thái từng phần, quyết định + lý do, bước tiếp theo

**Khi bắt đầu một phiên làm việc mới về dự án này, đọc file 07 trước** — đó là nguồn thông tin mới nhất và đầy đủ nhất về trạng thái thực tế của code.

## Quyết định kỹ thuật đã chốt (không re-litigate)

- **Backend**: Python 3.10 + FastAPI. Không dùng Python từ Microsoft Store alias.
- **Piano Accurate transcriber**: `piano_transcription_inference` (ByteDance/Kong et al., CPU-only qua `torch`) — checkpoint (~164MB) phải tải thủ công trên Windows (xem README, package tự tải bằng `wget` không hoạt động trên Windows).
- **Melody Quick transcriber**: Basic Pitch (ONNX Runtime, không dùng extra `[tf]`).
- **model_router**: tự fallback Basic Pitch nếu thiếu model piano, kèm warning rõ trong response — không âm thầm đổi.
- **Tempo/beat detection**: librosa. BPM candidates (half/double-time), time signature là heuristic best-effort, trả `null` nếu confidence <0.15 — **không hard-code 4/4**.
- **Note model**: `OriginalTiming` là frozen dataclass lồng trong `Note` — timing gốc bất biến về mặt kiến trúc, mọi biến đổi tạo Note mới qua `dataclasses.replace`, không mutate.
- **Polyphony**: `full` track KHÔNG BAO GIỜ qua skyline/lọc bass/dedupe. Skyline (`melody_derivation`) và ngưỡng Otsu thích ứng (`bass_derivation`) chỉ áp dụng khi dựng track dẫn xuất.
- **Giao diện**: local web server (FastAPI/uvicorn), frontend HTML/CSS/JS thuần (ES modules), không Node/React build step. Piano roll canvas hiện là **đọc-only**, chưa có chỉnh sửa nốt.
- **MIDI export**: `pretty_midi`, đa track (full_raw/full_quantized/melody/bass/chords), pedal CC64, tự trim chồng lấn cùng cao độ để tránh stuck note.
- **Job store**: dict theo `job_id` (không ghi đè), nhưng vẫn giới hạn 1 job `RUNNING` thật sự cùng lúc.

## Môi trường máy hiện tại

- Python 3.10.11, FFmpeg 8.1.2 (winget, 2026-07-17). PATH chưa refresh trong các shell session mở trước lúc cài — dùng full path hoặc mở terminal mới.
- **Torch (CPU) + piano_transcription_inference đã cài, checkpoint đã tải** tại `%USERPROFILE%\piano_transcription_inference_data\`. Xác nhận bằng `GET /api/health` → `piano_model_available: true`.
- Node v24 có sẵn nhưng **không dùng cho dự án này**.
- Git repo local, remote GitHub: `https://github.com/tuanna9112004/mucsicweb`.

## Quy ước code

- Threshold số tập trung tại `backend/app/config.py`.
- **Không mutate `Note`/`OriginalTiming`** — luôn dùng `dataclasses.replace()` hoặc `Note.with_target_timing()`. Test `does_not_mutate_*` phải pass khi thêm logic mới.
- `full` track là nguồn dữ liệu chính — không được thêm filter/skyline/dedupe nào vào đường xử lý của nó. Chỉ áp dụng cho track dẫn xuất (melody/bass).
- Tên field JSON phải khớp schema v2 trong `api/schemas.py` (vd `model_score` không phải `confidence`, vì đó là giá trị thô chưa hiệu chỉnh).
- Không viết stack trace ra response cho client.
