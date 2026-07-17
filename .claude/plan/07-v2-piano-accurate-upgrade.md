# V2 — Piano Accurate upgrade (2026-07-17, cùng ngày với v1 MVP)

## Bối cảnh — vì sao có bản nâng cấp này

Sau khi MVP v1 (giai điệu đơn âm, 135-140 BPM, `.claude/plan/00-06`) hoàn thành và đã fix 2 bug thực tế (lọc bass sai, gộp nhầm nốt lặp lại — xem `06-roadmap.md`), người dùng gửi một bản yêu cầu kỹ thuật rất chi tiết (đóng vai "Senior Audio AI Engineer") yêu cầu nâng cấp toàn bộ hệ thống thành **Audio-to-MIDI polyphonic chính xác cao**, không chỉ trích melody đơn âm nữa. Lý do cốt lõi: pipeline v1 (skyline + lọc bass + dedupe onset) phù hợp cho "trích 1 giai điệu để chuyển tempo" nhưng **xóa mất dữ liệu thật** (hợp âm, bass, nốt lặp lại) — không dùng được để tái tạo lại một bản piano đầy đủ.

Yêu cầu gốc rất dài (17 mục) — xem lại trong lịch sử hội thoại nếu cần đối chiếu nguyên văn. Tài liệu này ghi lại **những gì đã làm, quyết định nào, và còn thiếu gì** để phiên làm việc sau không phải đọc lại toàn bộ hội thoại.

## Trạng thái tổng quan: đã triển khai xong phần lõi (backend + test + frontend cơ bản), CHƯA làm UI chỉnh sửa nốt

| Hạng mục (theo yêu cầu gốc) | Trạng thái |
|---|---|
| 1. Giữ toàn bộ nốt polyphonic | ✅ Xong — `full` track không qua skyline/lọc/dedupe |
| 2. Giữ bass/melody/chord/nốt chồng | ✅ Xong |
| 3. MIDI gần bản gốc | ✅ Xong (piano_cnn model, F1=0.9677 theo paper gốc) |
| 4. BPM/beat/key/chord | ✅ Xong (key + chord chỉ ở chế độ Piano Accurate) |
| 5. Track full/melody/bass/chord riêng | ✅ Xong (chord là file MIDI riêng, không phải "track" trong JSON — xem quyết định bên dưới) |
| 6. Raw độc lập với quantized | ✅ Xong — `OriginalTiming` frozen, không hàm nào mutate |
| 7. Cho phép nghe/kiểm tra/**chỉnh sửa** | ⚠️ **Chỉ nghe + xem (piano roll đọc-only). CHƯA có chỉnh sửa (thêm/xóa/kéo/đổi pitch/undo-redo)** |
| Piano Accurate mode + piano model chuyên dụng | ✅ Xong — `piano_transcription_inference`, fallback Basic Pitch tự động |
| Melody Quick mode | ✅ Xong — giữ nguyên hành vi pipeline v1, gán nhãn `monophonic_melody` |
| Sửa lỗi mất polyphony (skyline/bass-filter/dedupe/merge) | ✅ Xong |
| Timing raw/quantized/target tách biệt | ✅ Xong |
| BPM candidates, downbeat, time signature | ✅ Xong (heuristic, không phải model chuyên dụng — xem giới hạn) |
| Key + chord detection | ✅ Xong (heuristic, không phải model ML) |
| Track full/melody/bass derivation | ✅ Xong |
| MIDI export multi-track + pedal + no-stuck-note | ✅ Xong |
| JSON schema v2 | ✅ Xong |
| Job không ghi đè, mỗi job ID độc lập | ✅ Xong (dict-keyed job_store) |
| 18 kịch bản test yêu cầu | ✅ Xong (103 test, tất cả pass) |
| UI: mode/quantize/BPM/hiển thị key-chord-bpm | ✅ Xong |
| UI: piano roll đa track | ✅ Xong (canvas, READ-ONLY) |
| UI: solo/mute, thêm/xóa/kéo nốt, undo/redo | ❌ **Chưa làm** — xem "Bước tiếp theo" |
| MusicXML export | ❌ Chưa làm |
| mir_eval precision/recall | ❌ Không thể đo — không có ground-truth MIDI cho file mẫu thật (chỉ có ground-truth cho fixture tổng hợp đơn âm, không đại diện cho polyphonic) |

## Quyết định quan trọng đã đưa ra + lý do

### 1. Chọn `piano_transcription_inference` (ByteDance/Kong et al.) làm model Piano Accurate
**Lý do**: model piano chuyên dụng, có sẵn trên PyPI, output có onset/offset/velocity/pedal — đúng thứ yêu cầu cần. Đã verify thực nghiệm: F1 note ~0.9677 theo paper gốc, kiểm tra thật cho polyphony=10, phát hiện đúng pedal.
**Đánh đổi đã chấp nhận**: cần cài thêm `torch` (CPU wheel, ~120MB) — dependency nặng nhất dự án. Đã chọn CPU-only thay vì CUDA dù máy có GPU NVIDIA RTX 3050, để tránh rủi ro cài đặt CUDA/driver phức tạp — có thể tối ưu sau nếu cần tốc độ (xem "Bước tiếp theo").
**Vấn đề Windows phát hiện + đã xử lý**: package tự tải checkpoint bằng `os.system("wget ...")` — Windows không có `wget` thật (chỉ có PowerShell alias, không hoạt động qua `os.system`/cmd.exe). Đã tự tải bằng `curl.exe -L` và trỏ `checkpoint_path` tường minh trong `PianoTranscriber` thay vì để package tự tải.

### 2. Basic Pitch vẫn giữ lại — làm fallback VÀ backend cho Melody Quick
**Lý do**: không xóa chức năng cũ đang hoạt động (yêu cầu rõ trong đề bài). `model_router.select_transcriber()` chọn theo mode + `is_available()`; nếu Piano Accurate được chọn nhưng thiếu checkpoint/torch, tự fallback về Basic Pitch **kèm warning rõ ràng** trong `quality_report.warnings`, không âm thầm đổi mà không nói.

### 3. Bass derivation dùng ngưỡng Otsu thích ứng, không dùng G3 cố định
**Lý do**: yêu cầu gốc cấm cứng "không tự động loại nốt chỉ vì thấp hơn G3". Otsu's method (tối đa hóa phương sai giữa 2 cụm trên histogram cao độ có trọng số thời lượng) tự tìm điểm chia bass/treble theo phân bố thực tế của từng bài, không phải hằng số toàn cục. Có fallback: nếu dải cao độ quá hẹp hoặc >85% nốt rơi vào "bass", coi như bài không có vùng bass tách biệt → trả về track rỗng thay vì ép một kết quả sai.
**Lưu ý**: `MELODY_MIN_MIDI_PITCH=55` (G3) **vẫn còn** nhưng CHỈ áp dụng khi dựng track `melody` dẫn xuất (loại trừ nốt bass khỏi được chọn làm giai điệu) — không áp dụng cho `full` track hay `bass` track. Đây là điểm dễ nhầm lẫn nếu đọc code không kỹn — xem `music/melody_derivation.py` vs `music/bass_derivation.py`.

### 4. Quantize không còn dedupe/trim cho track đa âm
**Lý do**: dedupe theo `start_beat` trùng nhau (v1) là logic ĐÚNG cho một dòng giai điệu đơn âm nhưng SAI cho polyphonic (xóa mất hợp âm). Đã tách thành 2 hàm: `quantize_notes()` (generic, không bao giờ xóa nốt, dùng cho mọi track) và `resolve_monophonic_overlaps()` (dedupe + trim, CHỈ gọi cho track `melody`/`monophonic_melody` trong `pipeline.py`).

### 5. Note model: `OriginalTiming` là frozen dataclass lồng trong `Note`
**Lý do**: yêu cầu "raw notes không bị mutate" cần được đảm bảo **về mặt kiến trúc** (compiler/runtime chặn), không chỉ là quy ước code. Mọi bước biến đổi (merge, quantize, retime) dùng `dataclasses.replace()` để tạo Note mới, không sửa note cũ. Đã test trực tiếp (`test_note_models.py`, và test "does_not_mutate" rải khắp `test_melody_derivation.py`/`test_note_cleanup.py`/`test_quantize.py`/`test_retiming.py`).

### 6. `note_cleanup.clean_notes()` (merge/filter) chỉ chạy khi `source_model == "basic_pitch"`
**Lý do**: đã điều tra bằng cách đọc trực tiếp onset-activation matrix của Basic Pitch (xem `06-roadmap.md` mục fix "gộp nhầm nốt lặp lại") — Basic Pitch có xu hướng phân mảnh nốt, cần merge/filter hậu xử lý. Model piano chuyên dụng (`piano_cnn`) có onset/offset regression trực tiếp, đáng tin cậy hơn — merge/filter thêm vào có thể LÀM HỎNG dữ liệu tốt sẵn có (đúng tinh thần "không làm giả kết quả phân tích" trong yêu cầu gốc).

### 7. Time signature/downbeat: heuristic salience-contrast, ngưỡng confidence tối thiểu 0.15
**Lý do**: không có budget để tích hợp downbeat tracker chuyên dụng (madmom DBN...). Heuristic đơn giản (so sánh salience trung bình giữa beat đầu nhóm vs beat còn lại, thử nhóm 3/4) đủ để **không hard-code 4/4** và trả `null` khi không đủ tin cậy — đúng yêu cầu "không cam kết khi chưa đủ dữ liệu" hơn là chính xác cao.

### 8. Melody Quick giữ scope hẹp — KHÔNG tính bass/chord/key
**Lý do**: yêu cầu gốc mô tả rõ đây là "chế độ phân tích nhanh", giữ nguyên pipeline melody hiện tại. Tính thêm harmony analysis sẽ làm mất ý nghĩa "quick". Full track (basic_pitch thô, không lọc) vẫn được xuất trong cả 2 mode để giữ nguyên tắc "full polyphonic luôn là nguồn dữ liệu chính".

### 9. Chord "track" không nằm trong `tracks: []` của JSON — nằm ở `harmony.chords`
**Lý do**: theo đúng ví dụ schema người dùng đưa ra (`harmony.chords` là mảng ChordSpan riêng, `tracks` là mảng note-tracks full/melody/bass). File MIDI hợp âm (`{name}_chords.mid`) vẫn được xuất bằng cách chuyển `ChordSpan.pitch_classes` thành block chord ở quãng tám gần C4.

### 10. Job store: dict theo `job_id`, nhưng vẫn giới hạn 1 job `RUNNING` cùng lúc
**Lý do**: yêu cầu "không ghi đè job đang chạy" + "mỗi job ID độc lập" KHÔNG có nghĩa là phải xử lý đồng thời thật (CPU-bound, máy người dùng có thể không đủ tài nguyên chạy 2 model nặng cùng lúc). `job_store.has_running_job()` được check ở `POST /analyze` — job khác có thể tồn tại (uploaded/done/error) song song, nhưng chỉ 1 job thực sự chạy phân tích tại một thời điểm, trả 409 nếu vi phạm.

## Bước tiếp theo (chưa làm, ưu tiên theo thứ tự gợi ý)

1. **UI chỉnh sửa nốt** (thêm/xóa/kéo/đổi pitch, undo/redo, xuất lại MIDI sau khi sửa) — đây là phần lớn nhất còn thiếu so với yêu cầu gốc mục 12. Dữ liệu đã sẵn sàng cho việc này (mỗi Note có đầy đủ raw/quantized/target, dễ serialize để FE sửa rồi POST lại một endpoint mới `PATCH /api/jobs/{id}/tracks/{track_type}/notes` hoặc tương tự — CHƯA có endpoint này).
2. **Solo/mute từng track khi playback** — hiện chưa có audio preview của MIDI (chỉ nghe được file gốc qua `<audio>`, chưa render MIDI ra âm thanh trong trình duyệt). Cần Web MIDI API hoặc synth JS (vd `soundfont-player`) để phát MIDI trực tiếp trên UI.
3. **MusicXML export** — chưa làm, cần thư viện riêng (`music21` phía Python, hoặc chuyển đổi thủ công từ Note list).
4. **mir_eval precision/recall thật** — cần bộ ground-truth MIDI polyphonic thật (vd MAESTRO dataset hoặc tự chơi + ghi MIDI song song với audio) để so sánh — hiện KHÔNG có, không nên tự bịa số liệu.
5. **Tối ưu tốc độ Piano Accurate** — hiện ~20s CPU cho clip 26s (gần real-time). Có thể thử CUDA (máy có RTX 3050) nếu tốc độ trở thành vấn đề với file dài hơn (giới hạn hiện tại 90s).
6. **Downbeat/time-signature chính xác hơn** — heuristic hiện tại (salience-contrast) khá thô, có thể cải thiện bằng cách tích hợp `madmom` (DBN downbeat tracker) nếu cần độ chính xác cao hơn — chưa thử vì thêm dependency nặng khác.
7. **Cập nhật `01-architecture.md`/`02-algorithms.md`** (tài liệu v1) — hiện đã lỗi thời một phần sau nâng cấp v2 (mô tả `melody_extraction.py` đã bị xóa, quantize/retiming/note_cleanup mô tả sai field names). Chưa rewrite toàn bộ vì ưu tiên code trước theo đúng yêu cầu người dùng — nếu cần tra cứu thuật toán v1 chi tiết, đối chiếu với code thật trong `app/pipeline/` và `app/music/` thay vì tin tuyệt đối vào doc cũ.

## File/module quan trọng cần biết khi làm tiếp

- [`app/transcribers/model_router.py`](../../backend/app/transcribers/model_router.py) — điểm vào chọn model, thêm transcriber mới thì đăng ký ở đây
- [`app/music/note_models.py`](../../backend/app/music/note_models.py) — `Note`/`OriginalTiming`/`PedalEvent`/`ChordSpan`, đọc trước khi sửa bất kỳ field nào
- [`app/pipeline/pipeline.py`](../../backend/app/pipeline/pipeline.py) — orchestrator, nơi quyết định track nào được tính cho mode nào
- [`app/api/schemas.py`](../../backend/app/api/schemas.py) — schema v2, mọi thay đổi field phải đồng bộ với `frontend/js/noteTable.js`, `pianoRoll.js`, `app.js`
