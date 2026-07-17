from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.api.schemas import AnalysisResult
from app.config import settings
from app.core.errors import TaskCancelledError
from app.core.job_models import StepKey
from app.music import bass_derivation, chord_detection, key_detection, melody_derivation
from app.music.note_models import Note
from app.pipeline import json_export, midi_export, normalization, note_cleanup, quantize, retiming, tempo_beats
from app.transcribers.model_router import select_transcriber


@dataclass
class PipelineResult:
    analysis: AnalysisResult
    output_files: dict[str, Path]


def _quantize_and_retime(
    notes: list[Note], unit_beats: Optional[float], target_bpm: float, is_monophonic: bool
) -> list[Note]:
    quantized = quantize.quantize_notes(notes, unit_beats)
    if is_monophonic:
        quantized = quantize.resolve_monophonic_overlaps(quantized, unit_beats)
    return retiming.retime_notes_to_target_bpm(quantized, target_bpm)


def run_pipeline(
    source_path: Path,
    work_dir: Path,
    original_filename: str,
    analysis_mode: str,
    target_bpm: Optional[float],
    quantize_mode: str,
    source_sample_rate: int = 0,
    source_channels: int = 0,
    on_step: Optional[Callable[[StepKey], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> PipelineResult:
    """Điều phối toàn bộ pipeline phân tích, hỗ trợ 2 chế độ:

    - "piano_accurate": model piano chuyên dụng (fallback Basic Pitch), giữ TOÀN
      BỘ nốt đa âm làm nguồn dữ liệu chính (`full`), suy ra melody/bass/chord/key
      như dữ liệu DẪN XUẤT — không skyline, không lọc bass, không dedupe trên `full`.
    - "melody_quick": Basic Pitch, ưu tiên tốc độ — chỉ xuất `full` (thô) và
      `monophonic_melody` (skyline + làm sạch), không tính bass/chord/key.
    """

    def emit(step: StepKey) -> None:
        if on_step is not None:
            on_step(step)

    def check_cancelled() -> None:
        if should_cancel is not None and should_cancel():
            raise TaskCancelledError("Tác vụ đã bị hủy theo yêu cầu người dùng.")

    warnings: list[str] = []

    emit(StepKey.CHECK_FILE)
    check_cancelled()

    normalized_path = work_dir / "normalized.wav"
    audio_samples = normalization.normalize_audio(source_path, normalized_path, settings.TARGET_SAMPLE_RATE)
    emit(StepKey.NORMALIZE)
    check_cancelled()

    tempo_result = tempo_beats.detect_tempo_and_beats(audio_samples, settings.TARGET_SAMPLE_RATE)
    emit(StepKey.TEMPO_BEATS)
    check_cancelled()

    transcriber, router_warnings = select_transcriber(analysis_mode)
    warnings.extend(router_warnings)
    transcription = transcriber.transcribe(normalized_path, work_dir)
    full_notes_raw = transcription.notes
    pedal_events = transcription.pedal_events
    emit(StepKey.TRANSCRIBE)
    check_cancelled()

    # Basic Pitch có xu hướng phân mảnh nốt nhiều hơn model piano chuyên dụng —
    # chỉ làm sạch (merge/filter) khi nguồn là basic_pitch; KHÔNG áp dụng cho
    # dữ liệu từ model piano (tin tưởng onset/offset regression của model).
    if full_notes_raw and full_notes_raw[0].source_model == "basic_pitch":
        try:
            full_notes = note_cleanup.clean_notes(full_notes_raw)
        except Exception:
            full_notes = full_notes_raw
    else:
        full_notes = full_notes_raw

    full_notes = tempo_beats.map_notes_to_beat_grid(full_notes, tempo_result.beat_times)

    tracks_raw: dict[str, list[Note]] = {"full": full_notes}

    if analysis_mode == "piano_accurate":
        melody_track = melody_derivation.derive_melody_track(full_notes)
        bass_track = bass_derivation.derive_bass_track(full_notes)
        tracks_raw["melody"] = melody_track
        if bass_track:
            tracks_raw["bass"] = bass_track
    else:
        melody_track = melody_derivation.derive_melody_track(full_notes)
        try:
            melody_track = note_cleanup.clean_notes(melody_track)
        except Exception:
            pass
        tracks_raw["monophonic_melody"] = melody_track

    emit(StepKey.DERIVE_TRACKS)
    check_cancelled()

    key_estimate = None
    chords = []
    if analysis_mode == "piano_accurate":
        key_estimate = key_detection.detect_key(full_notes)
        chords = chord_detection.detect_chords(full_notes, tempo_result.beat_times)
    emit(StepKey.HARMONY)
    check_cancelled()

    effective_target_bpm = target_bpm if target_bpm is not None else tempo_result.detected_bpm
    unit_beats = quantize.QUANTIZE_UNITS_BEATS[quantize_mode]

    tracks_final: dict[str, list[Note]] = {}
    for track_type, notes in tracks_raw.items():
        is_monophonic = track_type in ("melody", "monophonic_melody")
        tracks_final[track_type] = _quantize_and_retime(notes, unit_beats, effective_target_bpm, is_monophonic)

    emit(StepKey.QUANTIZE_RETIME)
    check_cancelled()

    duration_seconds = len(audio_samples) / settings.TARGET_SAMPLE_RATE

    analysis = json_export.build_analysis_result(
        original_filename=original_filename,
        duration_seconds=duration_seconds,
        sample_rate=source_sample_rate or settings.TARGET_SAMPLE_RATE,
        channels=source_channels or 1,
        analysis_mode=analysis_mode,
        target_bpm=target_bpm,
        quantization=quantize_mode,
        tempo_result=tempo_result,
        key_estimate=key_estimate,
        chords=chords,
        tracks=tracks_final,
        warnings=warnings,
    )

    stem = Path(original_filename).stem
    output_files: dict[str, Path] = {}

    full_raw_path = work_dir / f"{stem}_full_raw.mid"
    midi_export.write_midi_file(
        midi_export.notes_to_midi_events(tracks_raw["full"], timing="original"),
        full_raw_path,
        tempo_bpm=tempo_result.detected_bpm,
        track_name="Full Piano (Raw)",
        pedal_events=pedal_events,
    )
    output_files["full_raw"] = full_raw_path

    time_scale = tempo_result.detected_bpm / effective_target_bpm if effective_target_bpm else 1.0
    scaled_pedal_events = [
        type(p)(onset_seconds=p.onset_seconds * time_scale, offset_seconds=p.offset_seconds * time_scale)
        for p in pedal_events
    ]

    full_quantized_path = work_dir / f"{stem}_full_quantized.mid"
    midi_export.write_midi_file(
        midi_export.notes_to_midi_events(tracks_final["full"], timing="target"),
        full_quantized_path,
        tempo_bpm=effective_target_bpm,
        track_name="Full Piano (Quantized)",
        pedal_events=scaled_pedal_events,
    )
    output_files["full_quantized"] = full_quantized_path

    melody_key = "monophonic_melody" if "monophonic_melody" in tracks_final else "melody"
    if melody_key in tracks_final and tracks_final[melody_key]:
        melody_path = work_dir / f"{stem}_melody.mid"
        midi_export.write_midi_file(
            midi_export.notes_to_midi_events(tracks_final[melody_key], timing="target"),
            melody_path,
            tempo_bpm=effective_target_bpm,
            track_name="Melody",
        )
        output_files["melody"] = melody_path

    if "bass" in tracks_final and tracks_final["bass"]:
        bass_path = work_dir / f"{stem}_bass.mid"
        midi_export.write_midi_file(
            midi_export.notes_to_midi_events(tracks_final["bass"], timing="target"),
            bass_path,
            tempo_bpm=effective_target_bpm,
            track_name="Bass",
        )
        output_files["bass"] = bass_path

    if chords:
        chords_path = work_dir / f"{stem}_chords.mid"
        midi_export.write_midi_file(
            midi_export.chord_spans_to_midi_events(chords, time_scale=time_scale),
            chords_path,
            tempo_bpm=effective_target_bpm,
            track_name="Chords",
        )
        output_files["chords"] = chords_path

    json_path = work_dir / f"{stem}_analysis.json"
    json_export.write_analysis_json(analysis, json_path)
    output_files["json"] = json_path

    emit(StepKey.EXPORT)

    return PipelineResult(analysis=analysis, output_files=output_files)
