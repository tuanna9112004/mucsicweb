# Kiến trúc & Stack

## Cấu trúc thư mục

```
e:\WebAmNhac\
├── CLAUDE.md
├── .claude/plan/                  # tài liệu này
├── .gitignore                     # .venv/, __pycache__/, uploads/, *.pyc
├── README.md                      # hướng dẫn cài đặt & chạy
├── samples/                       # file audio thật để test thủ công end-to-end (không phải pytest fixture)
│   └── jtwayne-pianos-by-jtwayne-7-174717.mp3  # piano đơn, 18.86s, 603KB
├── backend/
│   ├── requirements.txt
│   ├── requirements-dev.txt       # pytest, pytest-asyncio, httpx, ruff
│   ├── pyproject.toml
│   ├── run_server.py              # entrypoint: check ffmpeg + uvicorn.run
│   ├── app/
│   │   ├── main.py                # FastAPI app, mount /api routers + StaticFiles(frontend)
│   │   ├── config.py              # tất cả threshold số (xem 02-algorithms.md)
│   │   ├── api/
│   │   │   ├── schemas.py         # Pydantic models (xem 03-api-schemas.md)
│   │   │   ├── routes_health.py   # GET /api/health
│   │   │   ├── routes_upload.py   # POST /api/upload
│   │   │   ├── routes_jobs.py     # POST /analyze, GET /jobs/{id}, POST /cancel
│   │   │   └── routes_download.py # GET /jobs/{id}/download/midi|json
│   │   ├── core/
│   │   │   ├── errors.py          # PipelineError hierarchy + exception handlers
│   │   │   ├── job_models.py      # JobStatus enum, Step enum, Job dataclass
│   │   │   └── job_store.py       # in-memory single-job store + Lock
│   │   ├── pipeline/
│   │   │   ├── note_models.py     # dataclass Note dùng chung xuyên suốt pipeline
│   │   │   ├── ingestion.py       # validate ext/size, save, ffprobe duration/format
│   │   │   ├── normalization.py   # -> mono 22050Hz WAV chuẩn
│   │   │   ├── tempo_beats.py     # librosa tempo + beat_track
│   │   │   ├── melody_extraction.py # Basic Pitch wrapper + skyline melody selection (xem 02-algorithms.md § 4a-pre)
│   │   │   ├── note_cleanup.py    # merge nốt liền kề cùng cao độ, rồi lọc nốt quá ngắn
│   │   │   ├── quantize.py        # snap lưới none/1/4/1/8/1/16 + trim chồng lấn
│   │   │   ├── retiming.py        # beat-relative -> giây tuyệt đối theo target BPM
│   │   │   ├── midi_export.py     # dựng file .mid bằng pretty_midi
│   │   │   ├── json_export.py     # dựng AnalysisResult JSON
│   │   │   └── pipeline.py        # điều phối toàn bộ pipeline, cập nhật tiến trình Job
│   │   └── utils/
│   │       ├── ffmpeg_check.py    # shutil.which("ffmpeg"/"ffprobe")
│   │       └── logging_conf.py
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   ├── generate_fixture.py     # sinh WAV giai điệu synth bằng numpy+soundfile
│       │   └── synth_melody_120bpm.wav # ~5s, sinh 1 lần, commit vào git
│       ├── test_ingestion.py
│       ├── test_tempo_beats.py
│       ├── test_melody_extraction.py   # @pytest.mark.slow
│       ├── test_note_cleanup.py
│       ├── test_quantize.py
│       ├── test_retiming.py
│       ├── test_midi_export.py
│       ├── test_json_export.py
│       ├── test_api_upload.py
│       └── test_api_full_pipeline.py    # bao gồm 11 trường hợp lỗi
└── frontend/
    ├── index.html
    ├── styles.css
    └── js/
        ├── api.js         # fetch wrappers: upload/analyze/poll/download
        ├── state.js       # state object nhỏ + render()
        ├── dropzone.js    # drag/drop + validate phía client
        ├── player.js      # gắn <audio> với file đã chọn
        ├── stepper.js     # render các bước pipeline từ job status
        ├── noteTable.js   # render bảng nốt (raw vs quantized)
        └── errors.js      # map mã lỗi -> thông báo cho người dùng
```

## Thư viện & phiên bản

Python runtime: **3.10.11** (đã cài qua winget, không dùng Store alias). Lý do chọn 3.10: Basic Pitch trên Windows dùng **ONNX Runtime** làm backend mặc định khi Python ≤3.10, tránh TensorFlow-on-Windows (nguồn lỗi cài đặt phổ biến, mất GPU support native sau TF 2.10).

`backend/requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20
numpy==1.26.4
librosa==0.10.2.post1
soundfile==0.12.1
pydub==0.25.1
basic-pitch==0.4.0
pretty_midi==0.2.11
```

`backend/requirements-dev.txt`:
```
pytest==8.3.4
pytest-asyncio==0.25.2
httpx==0.28.1
ruff==0.9.3
```

## Lưu ý cài đặt trên Windows

- Pin `numpy==1.26.4` (không dùng numpy 2.x) — tránh vấn đề ABI với numba/librosa.
- Cài `basic-pitch==0.4.0` **không** kèm extra `[tf]` — mặc định dùng `onnxruntime`, không kéo TensorFlow.
- Giữ đường dẫn venv ngắn (`backend\.venv`).
- FFmpeg (đã cài, v8.1.2, alias `ffmpeg`/`ffplay`/`ffprobe`) phải nằm trên PATH cho cả `pydub` và `librosa`/`soundfile` giải mã MP3. Cần mở terminal mới sau khi cài để PATH cập nhật.

## Frontend: vì sao vanilla JS là đủ

- Drag-and-drop: native `dragenter`/`dragover`/`drop` + `<input type="file">` fallback.
- Audio player có seek: `<audio controls>` có sẵn scrubber.
- Stepper trạng thái: `<ol><li>` toggle class theo job status JSON.
- Bảng nốt cuộn được: `<table>` trong `div` với `max-height` + `overflow-y:auto` — vài trăm nốt tối đa (90s cap) không cần virtualization.
- Nút tải: `<a href="..." download>` — browser tự xử lý.
- Phục vụ qua `FastAPI StaticFiles` tại `http://localhost:PORT` (không phải `file://`) nên `<script type="module">` + ES modules hoạt động bình thường, không cần bundler.

## Environment setup đã thực hiện

1. `winget install --id Python.Python.3.10 -e` → Python 3.10.11 ✅ (2026-07-17)
2. `winget install --id Gyan.FFmpeg -e` → FFmpeg 8.1.2 ✅ (2026-07-17)
3. Còn lại: `git init`, tạo `.gitignore`, tạo venv `backend\.venv`, `pip install -r requirements.txt -r requirements-dev.txt`.
