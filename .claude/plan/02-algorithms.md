# Thuật toán lõi (threshold đã chốt cụ thể)

Tất cả threshold số dưới đây phải được đặt tên hằng số tập trung trong `backend/app/config.py`, không hardcode rải rác trong các module pipeline.

## 4a. Gắn nốt Basic Pitch vào lưới beat của librosa

1. `tempo, beat_frames = librosa.beat.beat_track(y, sr=22050)` → `beat_times = librosa.frames_to_time(beat_frames, sr=22050)`.
2. `detected_bpm = median(60 / diff(beat_times))`.
3. Với mỗi nốt thô `(onset_s, offset_s, pitch_midi, amplitude)` từ Basic Pitch: tìm cặp beat bao quanh bằng `np.searchsorted(beat_times, onset_s)`, nội suy tuyến tính:
   `start_beat = i + (onset_s - beat_times[i]) / (beat_times[i+1] - beat_times[i])`
4. **Ngoại suy biên**: onset trước `beat_times[0]` hoặc sau `beat_times[-1]` → ngoại suy tuyến tính bằng khoảng inter-beat đầu/cuối tương ứng (`start_beat` có thể âm hoặc vượt index cuối).
5. `duration_beats = end_beat - start_beat` tính tương tự cho offset.
6. v1 **không** xác định downbeat/số nhịp trong measure — beat 0 chỉ là beat đầu tiên phát hiện được (khớp giả định 4/4 đơn giản hóa).

## 4b. Làm sạch nốt — merge trước, filter sau

Thứ tự quan trọng: merge trước vì một merge có thể "cứu" hai mảnh nốt quá ngắn thành một nốt hợp lệ.

- **Merge nốt liền kề cùng cao độ**: sắp xếp theo start time; merge nốt A vào B khi:
  - `B.pitch_midi == A.pitch_midi` (khớp chính xác, **không** cho phép lệch ±1 semitone — vì contour pitch-bend nội tại của Basic Pitch đã capture biến thiên vi mô, cho phép lệch sẽ gộp nhầm hai nốt thực sự khác nhau).
  - `B.start - A.end <= MERGE_GAP_MS` với `MERGE_GAP_MS = 40`.
  - Nốt gộp: `start=A.start, end=B.end`, `velocity=max(A.vel, B.vel)`, `confidence = (confA*durA + confB*durB)/(durA+durB)` (trung bình trọng số theo thời lượng).
- **Lọc nốt quá ngắn** (sau merge): loại nốt có `duration_ms < MIN_NOTE_DURATION_MS` với `MIN_NOTE_DURATION_MS = 60` (nốt 16th nhanh nhất ở 138 BPM ~109ms, nên 60ms nằm an toàn dưới ngưỡng nhạc lý hợp lý trong khi vẫn bắt được nhiễu transcription thường <30-50ms).
- Loại thêm nốt có `confidence < MIN_NOTE_CONFIDENCE` với `MIN_NOTE_CONFIDENCE = 0.25`, bất kể duration.
- Nếu danh sách rỗng sau lọc → raise `NoMelodyDetectedError` (→ lỗi `NO_MELODY_DETECTED`, xem [`04-error-handling.md`](04-error-handling.md)).
- **Nguồn confidence**: ưu tiên activation posterior nội bộ của Basic Pitch (trung bình theo time/pitch-bin span của nốt) — cần verify tên hằng số thực tế trong `basic_pitch/constants.py` khi cài đặt xong package (`AUDIO_SAMPLE_RATE`, `FFT_HOP`, `MIDI_OFFSET`...). **Fallback nếu API nội bộ khó dùng**: lấy trực tiếp `amplitude` (0–1) của note event làm `confidence`, và `velocity = clip(round(amplitude*127), 1, 127)`.

## 4c. Quantization (none / 1/4 / 1/8 / 1/16)

- Đơn vị lưới theo beat: `none` → no-op, `1/4` → `1.0`, `1/8` → `0.5`, `1/16` → `0.25`.
- Snap `start` và `end` **độc lập** (không phải start rồi cộng duration):
  ```
  snapped_start = round(start_beat_raw / unit) * unit
  snapped_end   = round((start_beat_raw + duration_beats_raw) / unit) * unit
  duration_quantized = max(unit, snapped_end - snapped_start)
  ```
  `max(unit, ...)` ngăn nốt độ dài 0 khi start/end của một nốt rất ngắn snap về cùng vạch lưới.
- **Trim chồng lấn sau quantize**: sắp xếp theo `snapped_start`; với mỗi cặp liên tiếp, nếu nốt N có `snapped_end > note[N+1].snapped_start`, cắt duration của N để kết thúc đúng tại điểm bắt đầu của N+1 (giai điệu đơn âm không nên chồng nốt sau quantize).
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
