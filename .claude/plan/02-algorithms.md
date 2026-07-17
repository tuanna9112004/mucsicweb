# Thuật toán lõi (threshold đã chốt cụ thể)

Tất cả threshold số dưới đây phải được đặt tên hằng số tập trung trong `backend/app/config.py`, không hardcode rải rác trong các module pipeline.

## Thứ tự pipeline thực tế (đã tinh chỉnh khi implement)

```
audio đã chuẩn hóa
  → tempo_beats.detect_tempo_and_beats()          [Stage 1]
  → melody_extraction.extract_raw_notes()          [Stage 2: predict() + skyline melody selection]
  → note_cleanup.clean_notes()                     [Stage 2: merge liền kề + filter]
  → gắn beat (start_beat_raw/duration_beats_raw)   [Stage 3: dùng beat_times đã có ở Stage 1]
  → quantize.quantize_notes()                      [Stage 3]
  → retiming.retime_to_target_bpm()                [Stage 3]
  → midi_export / json_export                      [Stage 3]
```

Khác với dự kiến ban đầu (gắn beat ngay sau khi lấy nốt thô), **note cleanup (merge/filter) được thực hiện trước khi gắn beat** — vì merge/filter hoạt động hoàn toàn trên trục thời gian giây (start/end/confidence), không phụ thuộc lưới beat, nên dọn danh sách nốt gọn trước sẽ hiệu quả hơn.

## 4a-pre. Chọn giai điệu chính từ đầu ra đa âm của Basic Pitch (phát hiện khi implement)

**Quan trọng — không có trong thiết kế ban đầu**: `basic_pitch.inference.predict(audio_path)` trả về `note_events` là **đa âm** (polyphonic) theo mặc định, kể cả với input "nhạc cụ đơn" — đã xác minh thực nghiệm trên file piano mẫu (`samples/`): 151 nốt chồng lấn trong 18.86s. Cần một bước **chọn giai điệu chính (melody line)** trước khi đưa vào note cleanup.

Đã triển khai heuristic **skyline** (`melody_extraction.select_melody_skyline`): quét các nốt theo thứ tự thời gian bắt đầu; khi hai nốt chồng lấn, nốt có `pitch_midi` cao hơn thắng cho đoạn giao nhau (nốt thấp hơn bị cắt hoặc bỏ hẳn nếu bị nốt cao hơn bao trùm toàn bộ). Đây là phép đơn giản hóa có chủ đích cho MVP (không tái tạo chính xác toàn bộ polyphony, chỉ nhằm rút ra một dòng giai điệu hợp lý) — khớp với phạm vi "không cam kết chính xác 100%" trong đặc tả.

Với input đã đơn âm sẵn (vd fixture tổng hợp, hoặc guitar/vocal một bè), skyline không có gì để trim — hàm chạy qua như no-op.

Cấu trúc `note_events` thực tế từ `predict()` (đã xác minh, khớp đúng thiết kế fallback ban đầu): `list[tuple[start_time_seconds, end_time_seconds, pitch_midi, amplitude, pitch_bend_list_or_None]]`. Không cần dùng activation posterior nội bộ phức tạp — `amplitude` (phần tử thứ 4) đã là giá trị 0–1 hợp lý dùng trực tiếp làm `confidence` nguồn.

## 4a. Gắn nốt (đã làm sạch) vào lưới beat của librosa

1. `tempo, beat_frames = librosa.beat.beat_track(y, sr=22050)` → `beat_times = librosa.frames_to_time(beat_frames, sr=22050)`.
2. `detected_bpm = median(60 / diff(beat_times))`.
3. Với mỗi nốt đã làm sạch `(start_s, end_s, pitch_midi, confidence)`: tìm cặp beat bao quanh bằng `np.searchsorted(beat_times, start_s)`, nội suy tuyến tính:
   `start_beat = i + (start_s - beat_times[i]) / (beat_times[i+1] - beat_times[i])`
4. **Ngoại suy biên**: onset trước `beat_times[0]` hoặc sau `beat_times[-1]` → ngoại suy tuyến tính bằng khoảng inter-beat đầu/cuối tương ứng (`start_beat` có thể âm hoặc vượt index cuối).
5. `duration_beats = end_beat - start_beat` tính tương tự cho offset.
6. v1 **không** xác định downbeat/số nhịp trong measure — beat 0 chỉ là beat đầu tiên phát hiện được (khớp giả định 4/4 đơn giản hóa).
7. Kết quả gán vào cả `start_beat_raw`/`duration_beats_raw` (giá trị trước quantize) và `start_beat`/`duration_beats` (sẽ bị quantize.py ghi đè nếu có chọn mức quantize).

**Phát hiện quan trọng về `librosa.beat.beat_track`**: tín hiệu hoàn toàn "sạch" về mặt số học (không có noise floor) có thể khiến thuật toán dynamic-programming của beat_track bị suy biến (trả về 0 beat) — xem ghi chú trong [`05-testing.md`](05-testing.md) và [`06-roadmap.md`](06-roadmap.md). Đã xác nhận thuật toán hoạt động ổn định, chính xác trên audio thật (piano mẫu: 103.36 BPM, 30 beat).

## 4b. Làm sạch nốt — merge trước, filter sau

Thứ tự quan trọng: merge trước vì một merge có thể "cứu" hai mảnh nốt quá ngắn thành một nốt hợp lệ. Chạy ngay sau melody selection (4a-pre), **trước** khi gắn beat (4a) — xem sơ đồ thứ tự pipeline ở trên.

- **Merge nốt liền kề cùng cao độ**: sắp xếp theo start time; merge nốt A vào B khi:
  - `B.pitch_midi == A.pitch_midi` (khớp chính xác, **không** cho phép lệch ±1 semitone — vì contour pitch-bend nội tại của Basic Pitch đã capture biến thiên vi mô, cho phép lệch sẽ gộp nhầm hai nốt thực sự khác nhau).
  - `B.start - A.end <= MERGE_GAP_MS` với `MERGE_GAP_MS = 40`.
  - Nốt gộp: `start=A.start, end=B.end`, `confidence = (confA*durA + confB*durB)/(durA+durB)` (trung bình trọng số theo thời lượng). Không cần track `velocity` riêng trong lúc merge — `velocity` được suy ra từ `confidence` một lần tại bước export MIDI/JSON (`velocity = clip(round(confidence*127), 1, 127)`), không phải một trường độc lập xuyên suốt pipeline.
- **Lọc nốt quá ngắn** (sau merge): loại nốt có `duration_ms < MIN_NOTE_DURATION_MS` với `MIN_NOTE_DURATION_MS = 60` (nốt 16th nhanh nhất ở 138 BPM ~109ms, nên 60ms nằm an toàn dưới ngưỡng nhạc lý hợp lý trong khi vẫn bắt được nhiễu transcription thường <30-50ms).
- Loại thêm nốt có `confidence < MIN_NOTE_CONFIDENCE` với `MIN_NOTE_CONFIDENCE = 0.25`, bất kể duration.
- Nếu danh sách rỗng sau lọc (hoặc input rỗng) → raise `NoMelodyDetectedError` (→ lỗi `NO_MELODY_DETECTED`, xem [`04-error-handling.md`](04-error-handling.md)).
- **Nguồn confidence**: xác nhận qua thực nghiệm — dùng trực tiếp `amplitude` (phần tử thứ 4 của mỗi note event, giá trị 0–1) làm `confidence`. Không cần activation posterior nội bộ phức tạp (nhánh "fallback" ban đầu trong kế hoạch hoá ra chính là lựa chọn đủ tốt và đơn giản nhất).

## 4c. Quantization (none / 1/4 / 1/8 / 1/16)

- Đơn vị lưới theo beat: `none` → no-op, `1/4` → `1.0`, `1/8` → `0.5`, `1/16` → `0.25`.
- Snap `start` và `end` **độc lập** (không phải start rồi cộng duration):
  ```
  snapped_start = round(start_beat_raw / unit) * unit
  snapped_end   = round((start_beat_raw + duration_beats_raw) / unit) * unit
  duration_quantized = max(unit, snapped_end - snapped_start)
  ```
  `max(unit, ...)` ngăn nốt độ dài 0 khi start/end của một nốt rất ngắn snap về cùng vạch lưới.
- **Loại nốt trùng `start_beat` sau quantize** (phát hiện khi implement, không có trong thiết kế ban đầu): với audio phức tạp/đa âm, nhiều nốt riêng biệt có thể snap về **đúng cùng một** `start_beat` sau khi quantize (không chỉ chồng lấn một phần) — đã xác minh trên piano mẫu thật (71 nốt trước fix, còn 53 sau fix, 0 trùng lặp). Chỉ trim duration là không đủ trong trường hợp này (hai nốt cùng start vẫn tồn tại song song). Sắp xếp theo `start_beat`; với các nốt có `start_beat` giống hệt nhau, chỉ giữ lại nốt có `confidence` cao hơn, loại các nốt còn lại.
- **Trim chồng lấn sau quantize** (sau bước loại trùng ở trên): với mỗi cặp liên tiếp, nếu nốt N có `snapped_end > note[N+1].snapped_start`, cắt duration của N để kết thúc đúng tại điểm bắt đầu của N+1 (giai điệu đơn âm không nên chồng nốt sau quantize).
- Lưu **cả giá trị trước và sau quantize** trên mỗi nốt (`start_beat_raw`, `duration_beats_raw` bên cạnh `start_beat`, `duration_beats` đã quantize) để UI so sánh — khi mode là `none`, hai giá trị bằng nhau, không cần nhánh đặc biệt ở downstream.

## 4d. Đổi sang tempo đích (135–140 BPM)

Vì vị trí nốt đã lưu **theo beat**, đổi tempo là scale tuyến tính đơn giản, **không ảnh hưởng cao độ** (đây là export MIDI, không phải audio time-stretch):

```
beat_duration_target = 60.0 / target_bpm
start_time_seconds = start_beat_quantized * beat_duration_target
duration_seconds   = duration_beats_quantized * beat_duration_target
end_time_seconds   = start_time_seconds + duration_seconds
```

File MIDI xuất ra có **một tempo cố định** (`pretty_midi.PrettyMIDI(initial_tempo=target_bpm)`) — không giữ biến động tempo vi mô gốc. Đây là chủ đích: "chuyển sang tempo đích" nghĩa là căn theo lưới tempo mới, không phải "giữ nguyên micro-timing gốc".

**Không cần audio time-stretch (pyrubberband/phase vocoder) ở đâu trong luồng MVP này** — chỉ liên quan nếu triển khai tính năng phụ "nghe thử audio ở tempo mới" (ngoài phạm vi MVP core).

## 4e. Ước lượng tông (tính năng thử nghiệm, làm sau khi core xong)

Krumhansl-Schmukler profile correlation, xây từ **nốt MIDI đã trích xuất theo trọng số duration** (không phải chroma audio thô — ổn định hơn vì melody đã đơn âm và quantize):

1. Cộng `duration_seconds` theo pitch-class (0–11) trên toàn bộ nốt → vector 12-chiều.
2. Chuẩn hóa vector.
3. Tương quan Pearson với 24 profile major/minor Krumhansl-Kessler.
4. `argmax` → tên key (vd "C Major"), tương quan cao nhất → `key_confidence`.

Luôn hiển thị là "ước lượng" (`estimated_key`), **không bao giờ khẳng định là tông gốc**. `estimated_key = null` nếu độ tin cậy quá thấp (không đủ dữ liệu).
