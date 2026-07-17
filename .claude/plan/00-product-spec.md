# Đặc tả sản phẩm (nguồn gốc yêu cầu)

## Mục tiêu

Xây dựng phần mềm web chạy hoàn toàn local, nhận file âm thanh có sẵn và tự động phân tích giai điệu chính thành các nốt nhạc có thể tái sử dụng.

Hệ thống cần:
- Phát hiện tempo gốc, xác định vị trí beat.
- Nhận diện giai điệu chính, chuyển thành nốt MIDI.
- Xác định thời điểm bắt đầu/kết thúc/độ dài từng nốt, căn theo nhịp.
- Chuyển sang tempo mục tiêu 135–140 BPM, giữ nguyên cao độ.
- Xuất file MIDI mở được trong FL Studio, Ableton, Cubase, Logic, Studio One, MuseScore...

Đây là hệ thống **phân tích và chuyển đổi**, không phải phần mềm sáng tác nhạc (không phải Suno).

## Bài toán thực tế

Người làm nhạc có MP3/WAV nhưng không có MIDI gốc, danh sách nốt, tempo chính xác, hay dữ liệu nhập piano roll. Quy trình thủ công hiện tại (nghe → dò nốt → xác định tempo → nhập piano roll → căn chỉnh → chuyển tempo) tốn thời gian và cần kỹ năng nghe nhạc.

## Ví dụ luồng sử dụng

1. Chọn file `con-co-be-be.mp3`, chọn tempo đầu ra 138 BPM, quantize 1/8, nhấn phân tích.
2. Hệ thống phát hiện: tempo gốc 100 BPM, nhịp 4/4, thời lượng 32s.
3. Giai điệu → nốt (vd `C4-D4-E4-G4-E4-D4-C4`), mỗi nốt có đầy đủ metadata (xem [`03-api-schemas.md`](03-api-schemas.md)).
4. Xuất `con-co-be-be_138bpm.mid` + `con-co-be-be_analysis.json`.

## Phạm vi MVP

### Bắt buộc
- Chạy hoàn toàn local, giao diện web mở bằng trình duyệt, không đăng nhập.
- Chọn/kéo thả file, hỗ trợ tối thiểu MP3 + WAV, kiểm tra file hợp lệ.
- Chuẩn hóa audio trước khi phân tích.
- Phát hiện tempo gốc + beat, nhận diện giai điệu chính, chuyển thành nốt MIDI.
- Xác định start/duration từng nốt, loại nốt nhiễu quá ngắn, gộp nốt liền nhau cùng cao độ.
- Quantize: none / 1/4 / 1/8 / 1/16.
- Tempo đầu ra 135–140 BPM (mặc định 138), không đổi cao độ.
- Hiển thị thông tin phân tích + danh sách nốt.
- Xuất `.mid` + `.json`.
- Có file mẫu để test, xử lý lỗi rõ ràng, có test cho pipeline cốt lõi.

### Có thể thử nghiệm (stretch, không bắt buộc)
- Ước lượng tông (key), piano roll đơn giản, nghe thử MIDI, ngưỡng confidence điều chỉnh được, gợi ý hợp âm (**chỉ là gợi ý tham khảo, không khẳng định là hợp âm gốc**).

### Ngoài phạm vi MVP (không triển khai)
- Đăng nhập/đăng ký, đa người dùng, thanh toán, cloud/VPS, mobile app.
- Xử lý nhiều tác vụ đồng thời.
- Tách toàn bộ nhạc cụ thành nhiều track MIDI.
- Huấn luyện model ML mới, xử lý real-time từ microphone.
- Cam kết chính xác 100% mọi bài hát.
- Biên tập MIDI chuyên sâu kiểu DAW.
- Tự sáng tác/tạo bài hát mới.

## Giới hạn đầu vào

- Định dạng bắt buộc: `.wav`, `.mp3`. Có thể bổ sung `.m4a`, `.flac` nếu thư viện ổn định.
- Dung lượng tối đa 30MB, thời lượng tối đa 90 giây.
- Ưu tiên: melody rõ ràng, tempo ổn định, nhịp 4/4.
- Kết quả tốt: piano/guitar đơn, vocal rõ, nhạc cụ đơn, ít nhiễu.
- Kết quả kém hơn: nhiều nhạc cụ chồng lấn, reverb lớn, Auto-Tune mạnh, rap/giọng nói không cao độ ổn định, tempo thay đổi liên tục, rubato, thu âm chất lượng thấp, nhiều bè.

## Giao diện web (tóm tắt, xem chi tiết trong đặc tả gốc nếu cần)

Một luồng chính duy nhất: khu vực chọn file → trình phát audio gốc → cấu hình (tempo đích, quantize) → trạng thái xử lý (stepper theo từng bước pipeline) → kết quả tổng quan → bảng danh sách nốt → khu vực tải MIDI/JSON. Không nhiều trang, không dashboard, ưu tiên pipeline chạy đúng trước khi tối ưu hình thức UI.

Các bước hiển thị trong stepper:
```
Đang kiểm tra file → Đang chuẩn hóa âm thanh → Đang phát hiện tempo/beat →
Đang phân tích giai điệu → Đang chuyển thành nốt MIDI → Đang làm sạch nốt →
Đang căn nốt theo beat → Đang tạo file kết quả → Hoàn thành
```

11 trường hợp lỗi cần xử lý rõ ràng (không stack trace): xem [`04-error-handling.md`](04-error-handling.md).
