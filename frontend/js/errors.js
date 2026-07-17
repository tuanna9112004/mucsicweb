const ERROR_MESSAGES = {
  NO_FILE_SELECTED: "Vui lòng chọn một file âm thanh trước khi tiếp tục.",
  UNSUPPORTED_FORMAT: "Định dạng file không được hỗ trợ. Chỉ chấp nhận MP3 hoặc WAV.",
  FILE_UNREADABLE: "Không thể đọc file này. File có thể bị hỏng hoặc không phải file âm thanh hợp lệ.",
  FILE_TOO_LARGE: "File vượt quá dung lượng tối đa cho phép (30MB).",
  FILE_TOO_LONG: "File vượt quá thời lượng tối đa cho phép (90 giây).",
  FFMPEG_NOT_FOUND: "Không tìm thấy FFmpeg trên máy. Vui lòng cài đặt FFmpeg và khởi động lại ứng dụng.",
  NO_MELODY_DETECTED:
    "Không phát hiện được giai điệu rõ ràng trong file này. Hãy thử một file khác có giai điệu nổi bật hơn.",
  ANALYSIS_ERROR: "Đã xảy ra lỗi trong quá trình phân tích. Vui lòng thử lại hoặc dùng file khác.",
  MIDI_EXPORT_FAILED: "Không thể tạo file MIDI từ kết quả phân tích.",
  OUT_OF_MEMORY: "Không đủ bộ nhớ để xử lý file này. Hãy thử một file ngắn hơn.",
  TASK_CANCELLED: "Tác vụ đã bị hủy.",
};

export function describeError(code, fallbackMessage) {
  return ERROR_MESSAGES[code] || fallbackMessage || "Đã xảy ra lỗi không xác định.";
}
