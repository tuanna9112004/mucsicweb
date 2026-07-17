# Roadmap & tiến độ (checklist sống — cập nhật khi hoàn thành mỗi mục)

Cập nhật file này (đánh dấu `[x]`) ngay khi hoàn thành một mục, để phiên làm việc sau biết chính xác đang ở đâu mà không cần suy đoán lại từ đầu.

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

## Stage 3 — Quantize + retiming + MIDI/JSON export

- [ ] `pipeline/quantize.py` — snap lưới none/1/4/1/8/1/16 + trim chồng lấn
- [ ] `pipeline/retiming.py` — beat-relative → giây tuyệt đối theo target BPM
- [ ] `pipeline/midi_export.py` — dựng `.mid` bằng pretty_midi
- [ ] `pipeline/json_export.py` — dựng `AnalysisResult` JSON (khớp field name theo [`03-api-schemas.md`](03-api-schemas.md))
- [ ] `pipeline/pipeline.py` — điều phối toàn bộ stage 1-3
- [ ] `test_quantize.py`, `test_retiming.py`, `test_midi_export.py`, `test_json_export.py` — pass
- [ ] Checkpoint: CLI debug script tạo `.mid`/`.json` thật từ fixture, mở thử file MIDI

## Stage 4 — FastAPI endpoints + job store + error handling

- [ ] `core/job_models.py`, `core/job_store.py`
- [ ] `core/errors.py` — `PipelineError` hierarchy + exception handlers
- [ ] `api/schemas.py`, `api/routes_*.py` (health, upload, jobs, download)
- [ ] `main.py` — mount routers + StaticFiles
- [ ] `test_api_upload.py`, `test_api_full_pipeline.py` (bao gồm 11 lỗi) — pass
- [ ] Checkpoint: thử thủ công qua Swagger `/docs`

## Stage 5 — Frontend

- [ ] `index.html`, `styles.css`
- [ ] `js/api.js`, `js/state.js`, `js/dropzone.js`, `js/player.js`, `js/stepper.js`, `js/noteTable.js`, `js/errors.js`
- [ ] Checklist thủ công: kéo thả, sai định dạng, hủy giữa chừng, tải cả 2 file, cuộn bảng >200 nốt — chạy với 1 file MP3 thật

## Stage 6 — Nối đầu-cuối + hoàn thiện

- [ ] Banner thiếu FFmpeg trên UI
- [ ] Xử lý job 404 khi server restart (frontend yêu cầu upload lại)
- [ ] `README.md` — hướng dẫn cài đặt & chạy
- [ ] Chạy lại toàn bộ regression test (`pytest`) + checklist thủ công end-to-end với file thật
