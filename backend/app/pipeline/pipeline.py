from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.api.schemas import AnalysisResult
from app.config import settings
from app.core.errors import TaskCancelledError
from app.core.job_models import StepKey
from app.pipeline import (
    json_export,
    melody_extraction,
    midi_export,
    normalization,
    note_cleanup,
    quantize,
    retiming,
    tempo_beats,
)


@dataclass
class PipelineResult:
    analysis: AnalysisResult
    midi_path: Path
    json_path: Path


def run_pipeline(
    source_path: Path,
    work_dir: Path,
    original_filename: str,
    target_bpm: int,
    quantize_mode: str,
    on_step: Optional[Callable[[StepKey], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> PipelineResult:
    """Chạy toàn bộ pipeline phân tích trên một file audio đã được validate/upload
    từ trước (xem app/pipeline/ingestion.py cho bước kiểm tra file).

    Thứ tự: chuẩn hóa audio -> phát hiện tempo/beat -> trích xuất giai điệu (Basic
    Pitch + skyline) -> làm sạch nốt -> gắn lưới beat -> quantize -> đổi tempo đích
    -> xuất MIDI + JSON.

    `on_step` (nếu có) được gọi sau khi mỗi bước hoàn tất, dùng để cập nhật tiến
    trình cho UI. `should_cancel` (nếu có) được kiểm tra giữa các bước — hủy tác vụ
    là cooperative, không ngắt được một lệnh gọi thư viện đang chạy giữa chừng.
    """

    def emit(step: StepKey) -> None:
        if on_step is not None:
            on_step(step)

    def check_cancelled() -> None:
        if should_cancel is not None and should_cancel():
            raise TaskCancelledError("Tác vụ đã bị hủy theo yêu cầu người dùng.")

    emit(StepKey.CHECK_FILE)
    check_cancelled()

    normalized_path = work_dir / "normalized.wav"
    audio_samples = normalization.normalize_audio(source_path, normalized_path, settings.TARGET_SAMPLE_RATE)
    emit(StepKey.NORMALIZE)
    check_cancelled()

    tempo_result = tempo_beats.detect_tempo_and_beats(audio_samples, settings.TARGET_SAMPLE_RATE)
    emit(StepKey.TEMPO_BEATS)
    check_cancelled()

    raw_notes = melody_extraction.extract_raw_notes(normalized_path)
    emit(StepKey.MELODY_ANALYSIS)
    emit(StepKey.NOTES_CONVERSION)
    check_cancelled()

    cleaned_notes = note_cleanup.clean_notes(raw_notes)
    emit(StepKey.CLEAN_NOTES)
    check_cancelled()

    tempo_beats.map_notes_to_beat_grid(cleaned_notes, tempo_result.beat_times)
    unit_beats = settings.QUANTIZE_UNITS_BEATS[quantize_mode]
    quantized_notes = quantize.quantize_notes(cleaned_notes, unit_beats)
    final_notes = retiming.retime_notes_to_target_bpm(quantized_notes, target_bpm)
    emit(StepKey.QUANTIZE)
    check_cancelled()

    duration_seconds = len(audio_samples) / settings.TARGET_SAMPLE_RATE

    analysis = json_export.build_analysis_result(
        original_filename=original_filename,
        duration_seconds=duration_seconds,
        detected_bpm=tempo_result.detected_bpm,
        target_bpm=target_bpm,
        quantization=quantize_mode,
        notes=final_notes,
    )

    stem = Path(original_filename).stem
    midi_path = work_dir / f"{stem}_{target_bpm}bpm.mid"
    json_path = work_dir / f"{stem}_analysis.json"

    midi_export.export_midi(final_notes, target_bpm, midi_path)
    json_export.write_analysis_json(analysis, json_path)
    emit(StepKey.EXPORT)

    return PipelineResult(analysis=analysis, midi_path=midi_path, json_path=json_path)
