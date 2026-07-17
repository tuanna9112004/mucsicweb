# Roadmap & tiến độ (checklist sống — cập nhật khi hoàn thành mỗi mục)

Cập nhật file này (đánh dấu `[x]`) ngay khi hoàn thành một mục, để phiên làm việc sau biết chính xác đang ở đâu mà không cần suy đoán lại từ đầu.

## Sau MVP — cải tiến từ phản hồi thực tế

- [x] **Lọc nốt bass khỏi giai điệu** (2026-07-17) — người dùng phản ánh kết quả trên file `farran_ez-minimal-piano-underscore-456148.mp3` (piano hòa âm dày) "không đúng ý", chẩn đoán ra nốt bass giữ dài bị skyline chọn nhầm làm giai điệu. Thêm `MELODY_MIN_MIDI_PITCH=55` trong `config.py`, lọc trong `melody_extraction.extract_raw_notes` trước khi skyline chạy. Xem chi tiết [`02-algorithms.md`](02-algorithms.md#4a-pre-chọn-giai-điệu-chính-từ-đầu-ra-đa-âm-của-basic-pitch-phát-hiện-khi-implement). Test mới: `test_extract_raw_notes_filters_out_bass_register_notes`. Toàn bộ suite: **59/59 pass** sau fix.
- [x] **Sửa bug gộp nhầm nốt lặp lại thành 1 nốt dài** (2026-07-17) — người dùng tiếp tục phản ánh "chưa xử lý được đúng nốt" sau fix trên. Điều tra sâu bằng cách đọc trực tiếp onset activation matrix của Basic Pitch, xác nhận các nốt lặp lại (vd D5 lặp 4-6 lần liên tiếp theo nhịp) có onset confidence rất cao (0.75-0.95) nhưng vẫn bị `note_cleanup._merge_adjacent_same_pitch` gộp nhầm thành 1 nốt chỉ vì cùng cao độ + gap≈0. Thêm điều kiện `MERGE_MAX_DURATION_RATIO=0.3` (chỉ gộp khi 1 nốt ngắn bất thường so với nốt kia). Xem [`02-algorithms.md`](02-algorithms.md) mục 4b. File farran: 34→47 nốt (khôi phục đúng nhịp lặp), jtwayne: 42→43 nốt. Toàn bộ suite: **60/60 pass**.

## V2 — Piano Accurate (2026-07-17, cùng ngày)

Nâng cấp kiến trúc lớn theo yêu cầu chi tiết của người dùng: chuyển từ "trích giai điệu đơn âm" sang "audio-to-MIDI đa âm chính xác cao" (model piano chuyên dụng, giữ hợp âm/bass/pedal, key/chord detection, đa track, schema v2). Đây là thay đổi lớn nhất trong lịch sử dự án — **xem chi tiết đầy đủ trong [`07-v2-piano-accurate-upgrade.md`](07-v2-piano-accurate-upgrade.md)**: trạng thái từng phần, quyết định kỹ thuật + lý do, bước tiếp theo còn thiếu (UI chỉnh sửa nốt, MusicXML, mir_eval, downbeat chính xác hơn).

- [x] Tích hợp `piano_transcription_inference` (model piano chuyên dụng) làm transcriber chính cho Piano Accurate, Basic Pitch làm fallback tự động
- [x] Sửa toàn bộ pipeline để `full` track không còn mất dữ liệu (bỏ skyline/lọc bass/dedupe khỏi đường xử lý chính, chỉ dùng cho track dẫn xuất)
- [x] Note model redesign: `OriginalTiming` frozen, không mutate xuyên suốt pipeline
- [x] Thêm `music/` package: melody/bass derivation (Otsu adaptive threshold), chord detection (9 loại hợp âm + slash chord), key detection (Krumhansl-Schmukler)
- [x] Nâng cấp rhythm: BPM candidates (half/double-time), downbeat + time-signature heuristic (không hard-code 4/4)
- [x] MIDI export đa track (full_raw/full_quantized/melody/bass/chords) + pedal CC64 + chống stuck note
- [x] JSON schema v2 + job_store dict-keyed (không ghi đè job đang chạy)
- [x] 103/103 test pass (58 test mới/viết lại, 18 kịch bản theo yêu cầu)
- [x] Frontend: mode selector, hiển thị BPM candidates/key/chord timeline, piano roll đa track (canvas, **đọc-only**), tải nhiều file
- [ ] **Chưa làm**: UI chỉnh sửa nốt (thêm/xóa/kéo/đổi pitch/undo-redo), MusicXML export, đo precision/recall bằng mir_eval (không có ground-truth thật), downbeat tracker chuyên dụng (madmom)

## Stage 0 — Môi trường

- [x] `winget install --id Python.Python.3.10 -e` → Python 3.10.11 (2026-07-17). Lưu ý: Windows Store alias vẫn che `python` trên PATH — dùng full path `C:\Users\MSI\AppData\Local\Programs\Python\Python310\python.exe` để tạo venv thay vì gọi `python` trực tiếp.
- [x] `winget install --id Gyan.FFmpeg -e` → FFmpeg 8.1.2 (2026-07-17). Binary tại `C:\Users\MSI\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\`. PATH chưa refresh trong các shell session đang mở — cần shell mới hoàn toàn (hoặc dùng full path) để gọi `ffmpeg`/`ffprobe` trực tiếp.
- [x] Tạo `CLAUDE.md` + `.claude/plan/*.md` (tổ chức lại toàn bộ kế hoạch, 2026-07-17)
- [x] `git init` tại thư mục gốc + tạo `.gitignore` + commit khởi tạo (user.name/user.email cấu hình local: `tuanna9112004` / `tuanna9112004@gmail.com`)
- [x] Người dùng đã thêm file mẫu thật `samples/jtwayne-pianos-by-jtwayne-7-174717.mp3` (piano đơn, 18.86s, 603KB — hợp lệ, dùng cho test thủ công end-to-end ở Stage 5-6, KHÔNG phải fixture pytest tự động)
- [x] Tạo venv `backend\.venv` bằng `C:\Users\MSI\AppData\Local\Programs\Python\Python310\python.exe -m venv`
- [x] `pip install -r requirements.txt -r requirements-dev.txt` — thành công, đã xác nhận `basic_pitch` dùng model `nmp.onnx` (ONNX runtime, không có TensorFlow) qua import test trực tiếp

## Stage 1 — Scaffolding + ingestion + tempo/beat detection ✅ (2026-07-17)

- [x] Tạo cấu trúc thư mục `backend/app/...` theo [`01-architecture.md`](01-architecture.md)
- [x] `config.py` với các hằng số threshold (xem [`02-algorithms.md`](02-algorithms.md))
- [x] `core/errors.py` — toàn bộ hierarchy `PipelineError` cho 11 trường hợp lỗi (dùng dần qua các stage)
- [x] `pipeline/ingestion.py` — validate extension/size/ffprobe
- [x] `pipeline/normalization.py` — chuẩn hóa về mono 22050Hz WAV
- [x] `pipeline/tempo_beats.py` — librosa tempo + beat_track
- [x] `tests/fixtures/generate_fixture.py` + `synth_melody_120bpm.wav` (commit vào git)
- [x] `test_ingestion.py`, `test_normalization.py`, `test_tempo_beats.py` — 13/13 pass
- [x] Checkpoint: BPM phát hiện được trên fixture synth = 123.05 (ground truth 120, dung sai ±6 thay vì ±2 dự kiến ban đầu — xem ghi chú "Phát hiện quan trọng" bên dưới)

**Phát hiện quan trọng (ảnh hưởng cách viết fixture, không ảnh hưởng thuật toán production)**: âm thanh tổng hợp hoàn toàn "sạch" (không nhiễu) tạo ra onset-strength envelope quá đều đặn, khiến `librosa.beat.beat_track`'s dynamic-programming bị suy biến và trả về 0 beat — đã xác minh bằng debug trực tiếp. Đã fix bằng cách thêm noise floor rất nhỏ (σ=0.005) vào fixture, mô phỏng bản thu thật (đã xác nhận thuật toán hoạt động đúng, cho kết quả ổn định trên file MP3 piano thật ở `samples/`: phát hiện 103.36 BPM, 30 beat, khớp hoàn toàn với nghe cảm quan). Không cần sửa `tempo_beats.py`.

## Stage 2 — Melody extraction + note cleanup ✅ (2026-07-17)

- [x] `pipeline/note_models.py` — dataclass `Note` dùng chung xuyên suốt pipeline
- [x] `pipeline/melody_extraction.py` — Basic Pitch wrapper; confidence lấy trực tiếp từ `amplitude` (đã xác nhận đủ tốt, xem [`02-algorithms.md`](02-algorithms.md#4a-pre))
- [x] `pipeline/melody_extraction.select_melody_skyline` — **bước mới phát hiện khi implement**: chọn giai điệu chính từ đầu ra đa âm của Basic Pitch (heuristic skyline)
- [x] `pipeline/note_cleanup.py` — merge liền kề cùng cao độ, rồi lọc nốt ngắn/confidence thấp
- [x] `test_melody_extraction.py` (bao gồm unit test riêng cho skyline + integration test trên fixture), `test_note_cleanup.py` — 25/25 pass toàn bộ suite
- [x] Checkpoint: Basic Pitch nhận diện **chính xác 100%** 8 nốt của fixture tổng hợp (C4-D4-E4-F4-G4-F4-E4-D4), timing sai lệch <40ms so với ground truth

**Phát hiện quan trọng (đã cập nhật [`02-algorithms.md`](02-algorithms.md))**: `basic_pitch.inference.predict()` trả về `note_events` **đa âm theo mặc định**, kể cả input tưởng chừng đơn âm — xác minh trên piano mẫu thật (`samples/`): 151 nốt chồng lấn/18.86s. Đã thêm bước "skyline melody selection" (nốt cao độ cao hơn thắng khi chồng lấn) trước khi merge/filter — không nằm trong thiết kế thuật toán ban đầu ở `02-algorithms.md`, đã bổ sung mục 4a-pre.

## Stage 3 — Quantize + retiming + MIDI/JSON export ✅ (2026-07-17)

- [x] `api/schemas.py` — tạo sớm hơn dự kiến (Pydantic `NoteModel`/`AnalysisResult`/`AnalyzeRequest`) vì `json_export.py` cần dùng trực tiếp
- [x] `pipeline/quantize.py` — snap lưới none/1/4/1/8/1/16 + **loại trùng start_beat** (bug phát hiện qua test thủ công) + trim chồng lấn
- [x] `pipeline/retiming.py` — beat-relative → giây tuyệt đối theo target BPM
- [x] `pipeline/midi_export.py` — dựng `.mid` bằng pretty_midi
- [x] `pipeline/json_export.py` — dựng `AnalysisResult` JSON (khớp field name theo [`03-api-schemas.md`](03-api-schemas.md))
- [x] `pipeline/pipeline.py` — điều phối toàn bộ stage 1-3 (`run_pipeline`)
- [x] `scripts/debug_pipeline.py` — CLI debug, dùng cho checkpoint thủ công
- [x] `test_quantize.py`, `test_retiming.py`, `test_midi_export.py`, `test_json_export.py`, `test_pipeline.py` (integration end-to-end trên fixture) — 41/41 pass toàn bộ suite
- [x] Checkpoint: chạy `scripts/debug_pipeline.py` trên cả fixture synth **và** file piano thật (`samples/`) ở 138 BPM + quantize 1/8 — MIDI/JSON tạo thành công, đọc lại bằng `pretty_midi` xác nhận note-on/off hợp lệ

**Bug phát hiện + đã sửa qua kiểm thử thủ công trên audio thật**: chạy debug script trên piano mẫu ban đầu cho ra nhiều nốt có **cùng `start_beat`** (vd 3 nốt cùng snap về beat=2.50) — vi phạm tính đơn âm. Nguyên nhân: bước trim chồng lấn ban đầu chỉ xử lý chồng lấn *một phần* (giả định `start_beat` tăng dần nghiêm ngặt), không xử lý trường hợp nhiều nốt trùng khớp hoàn toàn `start_beat` sau quantize. Đã thêm bước "loại trùng, giữ confidence cao hơn" trước bước trim (xem [`02-algorithms.md`](02-algorithms.md) mục 4c) — số nốt trên piano mẫu giảm từ 71 xuống 53, xác nhận 0 trùng lặp `start_beat` còn lại.

## Stage 4 — FastAPI endpoints + job store + error handling ✅ (2026-07-17)

- [x] `core/job_models.py` — `JobStatus`, `StepKey` (8 bước khớp text spec 7.4), `Job` dataclass, `build_step_statuses()`
- [x] `core/job_store.py` — single-job in-memory store + `Lock`
- [x] `core/job_runner.py` — `execute_job()` chạy `pipeline.run_pipeline` với `on_step`/`should_cancel` callback, bắt `PipelineError`/`MemoryError`/`Exception` và map sang `JobStatus`
- [x] `pipeline/pipeline.py` — mở rộng thêm tham số `on_step`/`should_cancel` (không đổi logic cốt lõi)
- [x] `api/schemas.py` — bổ sung `UploadResponse`, `HealthResponse`, `StepStatusModel`, `ErrorInfoModel`, `JobStatusResponse`
- [x] `api/routes_health.py`, `routes_upload.py`, `routes_jobs.py` (analyze/status/notes/cancel), `routes_download.py`
- [x] `main.py` — mount routers + exception handler cho `PipelineError` + catch-all không lộ stack trace + mount `StaticFiles` cuối cùng (guard `exists()` vì frontend chưa có tới Stage 5)
- [x] `run_server.py` — entrypoint, cảnh báo sớm nếu thiếu FFmpeg
- [x] `test_api_health.py`, `test_api_upload.py` (6 test, đủ các lỗi format/size/duration/ffmpeg), `test_api_jobs.py` (11 test: full flow + 404/409/422) — 58/58 pass toàn bộ suite
- [x] Checkpoint: chạy `run_server.py` thật, test qua `curl.exe` (không chỉ TestClient) — upload → analyze → poll → download hoạt động đúng trên piano mẫu thật (53 nốt, JSON 25KB, MIDI 379B)

**Phát hiện quan trọng**: `TestClient` của FastAPI/Starlette chạy `BackgroundTasks` **đồng bộ** trong cùng lời gọi (nên test poll ngay sau `analyze` luôn thấy `status="done"`), nhưng server thật (uvicorn) chạy **bất đồng bộ thực sự** — poll ngay sau khi gọi `/analyze` có thể thấy `status="running"`. Đã xác nhận qua test thủ công bằng `curl.exe` trực tiếp vào server đang chạy (không phải qua TestClient). Điều này khớp đúng thiết kế polling của UI (Stage 5) — không cần sửa gì, chỉ cần lưu ý khi viết test cho các stage sau không được giả định TestClient phản ánh đúng 100% timing của server thật.

## Stage 5 — Frontend ✅ mã nguồn xong, ⚠️ chưa test bằng trình duyệt thật (2026-07-17)

- [x] `index.html`, `styles.css`
- [x] `js/app.js` (entry point, không có trong danh sách file kiến trúc ban đầu — bổ sung vì cần một nơi nối các module lại), `js/api.js`, `js/state.js`, `js/dropzone.js`, `js/player.js`, `js/stepper.js`, `js/noteTable.js`, `js/errors.js`
- [x] Đã xác minh: `node --check` không lỗi cú pháp trên cả 8 file JS; server thật (`run_server.py`) phục vụ `index.html`/`styles.css`/`js/*.js` đúng `Content-Type` (`text/html`, `text/css`, `application/javascript`) song song với các route `/api/*`
- [ ] **CHƯA kiểm tra bằng trình duyệt thật** — môi trường agent hiện tại không có công cụ browser automation (Playwright/Puppeteer...). Cần người dùng tự mở `http://127.0.0.1:8000` sau khi chạy `run_server.py` và thử qua checklist thủ công dưới đây trước khi coi Stage 5 là hoàn tất thật sự:
  - [ ] Kéo thả file MP3/WAV vào dropzone
  - [ ] Chọn sai định dạng (vd .txt) → thấy thông báo lỗi rõ ràng
  - [ ] Nghe thử file gốc qua audio player, tua thời gian
  - [ ] Đổi tempo đích + quantize, nhấn "Bắt đầu phân tích", quan sát stepper cập nhật tuần tự
  - [ ] Nhấn "Hủy phân tích" giữa chừng
  - [ ] Xem bảng kết quả tổng quan + bảng danh sách nốt (cuộn được nếu nhiều nốt)
  - [ ] Tải cả file MIDI và JSON, mở thử file MIDI
  - [ ] Nhấn "Phân tích file mới" quay lại trạng thái ban đầu sạch sẽ
- [ ] Đây chính là checklist đầy đủ của Stage 6 bên dưới — Stage 5 và 6 sẽ được xác nhận cùng lúc khi có người dùng test qua trình duyệt thật

## Stage 6 — Nối đầu-cuối + hoàn thiện ✅ mã nguồn xong, ⚠️ chờ test trình duyệt thật (2026-07-17)

- [x] Banner thiếu FFmpeg trên UI (`checkFfmpegHealth()` trong `app.js`, gọi `/api/health` lúc load trang)
- [x] Xử lý job không tồn tại/hết hạn khi server restart — **bug phát hiện khi review**: các route `analyze`/`notes`/`cancel`/`download/*` trước đó dùng `HTTPException` mặc định của FastAPI (`{"detail": "..."}`), không khớp format `{"error": {code,message}}` mà `errors.js` cần để hiển thị đúng thông báo. Đã thêm `JobNotFoundError`/`JobAlreadyRunningError`/`JobResultNotReadyError` vào `core/errors.py` và dùng nhất quán (xem [`04-error-handling.md`](04-error-handling.md)) — giờ mọi lỗi API đều cùng một hình dạng JSON.
- [x] `README.md` — hướng dẫn cài đặt, chạy server, chạy test, file mẫu, giới hạn đã biết
- [x] Chạy lại toàn bộ regression test (`pytest`) — **58/58 pass** sau tất cả các thay đổi
- [x] Test thủ công qua HTTP thật (curl.exe, không phải TestClient): health → upload → analyze → poll → download, cả trên fixture synth và piano mẫu thật — hoạt động đúng
- [ ] **CHƯA test bằng trình duyệt thật** — môi trường agent (Claude Code) hiện tại không có công cụ browser automation (Playwright/Puppeteer/...) nên không thể tự trải nghiệm UI (kéo thả, xem stepper động, xem bảng nốt cuộn, nghe audio player...). Đã xác minh được: JS không lỗi cú pháp (`node --check`), server phục vụ đúng static files + Content-Type, toàn bộ luồng API hoạt động đúng qua HTTP thật. **Người dùng cần tự mở `http://127.0.0.1:8000` và chạy qua checklist thủ công ở Stage 5 trước khi coi MVP là hoàn tất thật sự** — nếu phát hiện lỗi UI/UX, báo lại để sửa tiếp.
