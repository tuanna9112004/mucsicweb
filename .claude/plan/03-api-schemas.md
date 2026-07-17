# API & Schema dữ liệu

Job model: **một job hiện tại duy nhất** trong bộ nhớ (dict + `threading.Lock`), không cần queue — khớp phạm vi "không xử lý nhiều tác vụ đồng thời".

## API Endpoints

| Method & Path | Chức năng |
|---|---|
| `GET /api/health` | `{ffmpeg_found, ffprobe_found}` — poll khi load trang để hiện banner lỗi FFmpeg sớm |
| `POST /api/upload` | Validate extension → stream lưu + đếm byte (chặn >30MB) → ffprobe kiểm tra duration/format (chặn >90s hoặc không đọc được). Trả `{job_id, filename, duration_seconds, size_bytes}` |
| `POST /api/jobs/{id}/analyze` | Body `AnalyzeRequest`. Chạy pipeline bằng FastAPI `BackgroundTask`. Trả 409 nếu đã có job đang chạy |
| `GET /api/jobs/{id}` | Poll mỗi 500ms — trả `JobStatusResponse`, dùng để vẽ stepper |
| `GET /api/jobs/{id}/notes` | Toàn bộ danh sách nốt (đủ nhỏ, không cần phân trang) |
| `GET /api/jobs/{id}/download/midi` | `FileResponse` kèm `Content-Disposition: attachment`, tên `{name}_{bpm}bpm.mid` |
| `GET /api/jobs/{id}/download/json` | Tương tự, tên `{name}_analysis.json` |
| `POST /api/jobs/{id}/cancel` | Đặt cờ `cancel_requested`, kiểm tra giữa các stage (cooperative, best-effort — không ngắt giữa một lệnh gọi basic-pitch đang chạy) |

Lifecycle: `POST /api/upload` mới sẽ hủy job cũ (single-slot store). Server restart → mất toàn bộ job (in-memory only, có chủ đích) — frontend phải xử lý `404` khi poll bằng cách yêu cầu upload lại.

## Pydantic Schemas

**Đối chiếu chính xác với 2 ví dụ JSON trong đặc tả gốc** (mục 6.1, 6.2 của spec) — không tự đặt tên trường khác.

### NoteModel (mục 6.2 spec)

```python
class NoteModel(BaseModel):
    note: str                    # "C4"
    midi_number: int             # 60
    start_time_seconds: float    # giá trị cuối cùng (đã quantize + đổi tempo)
    end_time_seconds: float
    duration_seconds: float
    start_beat: float            # giá trị đã quantize (dùng để export)
    duration_beats: float
    velocity: int                # 1-127
    confidence: float            # 0.0-1.0
    quantized: bool
    start_beat_raw: float         # trước quantize, để đối chiếu (yêu cầu "giá trị trước/sau quantize")
    duration_beats_raw: float
    merged: bool                  # true nếu là kết quả gộp nốt liền kề
```

Ví dụ tham chiếu từ spec gốc:
```json
{
  "note": "E4", "midi_number": 64,
  "start_time_seconds": 1.25, "end_time_seconds": 1.72, "duration_seconds": 0.47,
  "start_beat": 2.0, "duration_beats": 1.0,
  "velocity": 88, "confidence": 0.87, "quantized": true
}
```

### AnalysisResult (mục 6.1 + 6.4 spec, gộp overview + notes)

```python
class AnalysisResult(BaseModel):
    original_filename: str
    duration_seconds: float
    detected_bpm: float
    target_bpm: int
    time_signature: str = "4/4"
    estimated_key: str | None       # None nếu không đủ tin cậy
    quantization: Literal["none","1/4","1/8","1/16"]
    note_count: int
    processing_status: Literal["completed","failed"]
    pipeline_version: str = "1.0.0"
    analysis_method: dict            # {"tempo_beat_detection": "librosa.beat.beat_track", "melody_extraction": "basic-pitch==0.4.0"}
    warnings: list[str]
    notes: list[NoteModel]
```

Ví dụ tham chiếu (overview, mục 6.1 spec):
```json
{
  "original_filename": "sample.mp3", "duration_seconds": 45.2,
  "detected_bpm": 100.4, "target_bpm": 138, "time_signature": "4/4",
  "estimated_key": "C Major", "quantization": "1/8",
  "note_count": 42, "processing_status": "completed"
}
```

### Request/Job models

```python
class AnalyzeRequest(BaseModel):
    target_bpm: int = Field(ge=135, le=140, default=138)
    quantize: Literal["none","1/4","1/8","1/16"] = "none"

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["idle","uploaded","running","done","error","cancelled"]
    steps: list[StepStatus]       # dùng cho stepper UI
    progress_pct: int
    error: ErrorInfo | None
    result_summary: AnalysisResult | None
```

## Tên file output

```
{original_name}_{target_bpm}bpm.mid
{original_name}_analysis.json
```
