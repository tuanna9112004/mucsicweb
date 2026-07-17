from dataclasses import dataclass
from pathlib import Path

from app.api.schemas import AnalysisResult
from app.config import settings
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
) -> PipelineResult:
    """Chạy toàn bộ pipeline phân tích trên một file audio đã được validate/upload
    từ trước (xem app/pipeline/ingestion.py cho bước kiểm tra file).

    Thứ tự: chuẩn hóa audio -> phát hiện tempo/beat -> trích xuất giai điệu (Basic
    Pitch + skyline) -> làm sạch nốt -> gắn lưới beat -> quantize -> đổi tempo đích
    -> xuất MIDI + JSON.
    """
    normalized_path = work_dir / "normalized.wav"
    audio_samples = normalization.normalize_audio(source_path, normalized_path, settings.TARGET_SAMPLE_RATE)

    tempo_result = tempo_beats.detect_tempo_and_beats(audio_samples, settings.TARGET_SAMPLE_RATE)

    raw_notes = melody_extraction.extract_raw_notes(normalized_path)
    cleaned_notes = note_cleanup.clean_notes(raw_notes)

    tempo_beats.map_notes_to_beat_grid(cleaned_notes, tempo_result.beat_times)

    unit_beats = settings.QUANTIZE_UNITS_BEATS[quantize_mode]
    quantized_notes = quantize.quantize_notes(cleaned_notes, unit_beats)

    final_notes = retiming.retime_notes_to_target_bpm(quantized_notes, target_bpm)

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

    return PipelineResult(analysis=analysis, midi_path=midi_path, json_path=json_path)
