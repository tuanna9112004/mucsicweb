# Melody Tempo Analyzer (v2 — Piano Accurate)

Web app chạy hoàn toàn local: nhận file MP3/WAV, phân tích **polyphonic piano** (đầy đủ hợp âm, bass, pedal) bằng model piano chuyên dụng, tách track full/melody/bass, nhận diện tông + hợp âm theo timeline, quantize/đổi tempo tùy chọn, xuất nhiều file MIDI + JSON.

Có 2 chế độ:
- **Piano Accurate** — model piano chuyên dụng (`piano_transcription_inference`, fallback Basic Pitch nếu chưa cài), giữ toàn bộ nốt đa âm làm nguồn dữ liệu chính, suy ra melody/bass/hợp âm/tông.
- **Melody Quick** — Basic Pitch, chỉ trích một dòng giai điệu đơn âm, nhanh hơn, không tính hợp âm/tông.

Xem [`CLAUDE.md`](CLAUDE.md) và [`.claude/plan/`](.claude/plan/) cho kiến trúc v1 gốc (một số phần đã lỗi thời sau khi nâng cấp lên v2 — xem lịch sử git để biết chi tiết thay đổi).

## Yêu cầu môi trường

- **Python 3.10** (khuyến nghị dùng bản cài từ python.org, không dùng Python từ Microsoft Store).
- **FFmpeg** (`ffmpeg` + `ffprobe`) phải có trên PATH.
- (Tùy chọn nhưng khuyến nghị) **Model piano chuyên dụng** cho chế độ Piano Accurate — xem mục riêng bên dưới. Nếu bỏ qua, Piano Accurate vẫn chạy được nhưng tự động dùng Basic Pitch (kém chính xác hơn về polyphony/pedal).

Cài Python + FFmpeg trên Windows bằng winget:

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

`requirements.txt` đã bao gồm `torch` (bản CPU-only, ~120MB) + `piano_transcription_inference` cho chế độ Piano Accurate.

### Cài model Piano Accurate (checkpoint ~164MB)

Package `piano_transcription_inference` tự tải checkpoint bằng lệnh `wget`, nhưng **Windows không có `wget` thật** (chỉ có alias PowerShell trỏ tới `Invoke-WebRequest`, không hoạt động khi package gọi qua `os.system`). Cần tự tải thủ công:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\piano_transcription_inference_data"
curl.exe -L -o "$HOME\piano_transcription_inference_data\note_F1=0.9677_pedal_F1=0.9186.pth" `
  "https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1"
```

Kiểm tra `GET /api/health` sau khi khởi động server — trường `piano_model_available` phải là `true`.

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

Bỏ qua các test tích hợp chậm (cần chạy model thật, ~1 phút cho cả suite khi bao gồm cả test này):

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v -m "not slow"
```

## File mẫu để thử nghiệm

- `samples/jtwayne-pianos-by-jtwayne-7-174717.mp3` — piano đơn, ~19 giây.
- `samples/farran_ez-minimal-piano-underscore-456148.mp3` — piano hòa âm dày (chords + bass giữ dài), ~26 giây — dùng để kiểm tra polyphony/bass/pedal/chord.
- `backend/tests/fixtures/synth_melody_120bpm.wav` — giai điệu tổng hợp, ground-truth biết trước (8 nốt, 120 BPM), dùng cho test tự động.
- `backend/scripts/debug_pipeline.py` — chạy pipeline qua CLI, không qua web UI:
  ```powershell
  .venv\Scripts\python.exe scripts\debug_pipeline.py ..\samples\farran_ez-minimal-piano-underscore-456148.mp3 --mode piano_accurate --target-bpm 138 --quantize 1/8
  # hoặc giữ tempo gốc:
  .venv\Scripts\python.exe scripts\debug_pipeline.py ..\samples\jtwayne-pianos-by-jtwayne-7-174717.mp3 --mode melody_quick --keep-original-bpm --quantize none
  ```

## Kiến trúc pipeline (v2)

```
audio gốc
  → ingestion (validate) → normalization (mono 22050Hz)
  → tempo_beats (BPM + candidates half/double-time + downbeat/time-signature best-effort)
  → transcribers.model_router chọn PianoTranscriber (fallback BasicPitchTranscriber)
  → note_cleanup (CHỈ khi nguồn basic_pitch) → tempo_beats.map_notes_to_beat_grid
  → music.melody_derivation / bass_derivation (adaptive) / chord_detection / key_detection
  → pipeline/quantize (giữ polyphony, không dedupe) → pipeline/retiming (tempo đích tùy chọn)
  → midi_export (multi-track + pedal CC64) + json_export (schema v2)
```

Xuất ra tối đa 6 file: `{name}_full_raw.mid`, `{name}_full_quantized.mid`, `{name}_melody.mid`, `{name}_bass.mid`, `{name}_chords.mid`, `{name}_analysis.json` (bass/chords chỉ có ở chế độ Piano Accurate và khi bài thực sự có vùng bass/hợp âm rõ ràng).

## Giới hạn đã biết

- Chỉ một job chạy phân tích thực sự tại một thời điểm (nhiều job có thể tồn tại song song ở trạng thái khác, nhưng chỉ 1 job `running`).
- Trạng thái job lưu trong bộ nhớ — khởi động lại server sẽ mất job đang có.
- Giới hạn đầu vào: MP3/WAV, tối đa 30MB, tối đa 90 giây.
- Chord detection dùng heuristic template-matching đơn giản (9 loại hợp âm phổ biến), không phải model ML chuyên dụng — có thể sai với hòa âm phức tạp/jazz nặng.
- Time signature/downbeat là heuristic best-effort (dựa trên độ tương phản salience giữa các beat), không phải downbeat tracker chuyên dụng (loại DBN như madmom) — trả `null` khi không đủ tin cậy thay vì đoán bừa.
- Chưa có UI chỉnh sửa nốt (thêm/xóa/kéo/đổi pitch, undo/redo) — mới có piano roll đọc-only. Dữ liệu (raw/quantized/target tách biệt) đã sẵn sàng cho việc này ở phiên bản sau.
- Chưa xuất MusicXML.
- Chưa đo precision/recall bằng `mir_eval` với ground-truth MIDI thật (không có ground truth cho các file mẫu MP3) — không có số liệu độ chính xác định lượng, chỉ có quan sát định tính (số nốt, polyphony, pitch range...).
