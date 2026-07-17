# Chiến lược test

## Unit test (nhanh, hàm thuần, không cần audio thật)

- `test_note_cleanup.py` — danh sách nốt tay tạo, kiểm tra merge + filter đúng threshold (`MERGE_GAP_MS=40`, `MIN_NOTE_DURATION_MS=60`, `MIN_NOTE_CONFIDENCE=0.25`).
- `test_quantize.py` — giá trị snap kỳ vọng tính tay cho cả 4 mode (none/1/4/1/8/1/16), bao gồm case trim chồng lấn.
- `test_retiming.py` — cặp BPM đã biết (vd 120→138), kiểm tra scale tuyến tính đúng công thức mục [`02-algorithms.md`](02-algorithms.md#4d-đổi-sang-tempo-đích-135140-bpm).
- Validate Pydantic: `target_bpm=134` / `141` bị từ chối (ngoài `[135,140]`), `quantize` string không hợp lệ bị từ chối.

## Integration test (cần audio thật, đánh dấu `@pytest.mark.slow`)

- `test_tempo_beats.py` — trên fixture có BPM biết trước, kỳ vọng sai số ±2.
- `test_melody_extraction.py` — trên fixture có cao độ biết trước, kỳ vọng pitch khớp chính xác, timing sai số ±50ms.
- `test_midi_export.py` — round-trip: ghi rồi đọc lại bằng `pretty_midi.PrettyMIDI(path)`, kiểm tra nốt sống sót trong epsilon.
- `test_api_full_pipeline.py` — full flow qua `TestClient`: upload → analyze → poll → download. Bao gồm toàn bộ **11 trường hợp lỗi** (xem [`04-error-handling.md`](04-error-handling.md)):
  - file 0 byte
  - file giả quá khổ (>30MB)
  - clip synth >90s
  - file `.txt` đổi tên thành `.mp3`
  - `target_bpm=999`
  - mock `shutil.which` trả `None` để giả lập thiếu FFmpeg (không đụng PATH thật)

## Fixture âm thanh (chưa có sẵn — phải tạo mới)

Không dùng MP3 có bản quyền. Tạo `tests/fixtures/generate_fixture.py`:

- Tổng hợp sóng bằng **numpy + soundfile**: sine cơ bản + hài âm bậc 2 (×0.3) + bậc 3 (×0.15) để có timbre phong phú hơn sine thuần, dễ tracking pitch hơn.
- Fade in/out 10ms mỗi nốt.
- Ghép các nốt tại **thời điểm beat đã biết trước chính xác** — tự bản thân tham số synthesis là ground-truth để assert.
- Output: `synth_melody_120bpm.wav` (~5 giây), **sinh 1 lần và commit vào git** (hoàn toàn tự tạo, không vướng bản quyền) kèm script generator để tái tạo lại nếu cần.

## Checklist thủ công (không tự động hóa, thực hiện ở cuối mỗi stage liên quan)

- Sau Stage 3 (xem [`06-roadmap.md`](06-roadmap.md)): chạy CLI debug script trên fixture, mở `.mid` xuất ra bằng phần mềm hỗ trợ MIDI hoặc đọc lại bằng `pretty_midi` để xác nhận note-on/off hợp lệ.
- Sau Stage 4: mở Swagger `/docs`, thử tuần tự upload → analyze → poll → download cho cả thành công và cả 11 lỗi.
- Sau Stage 5-6: chạy server thật, thử với 1 file MP3/WAV **thật** (không phải fixture synth) từ đầu-cuối trên trình duyệt — kéo thả, nghe thử, chọn 138 BPM + quantize 1/8, phân tích, xem bảng nốt, tải MIDI + JSON, mở MIDI trong DAW/MuseScore nếu có.
