from pathlib import Path

from app.api.schemas import (
    AnalysisResult,
    BpmCandidateModel,
    ChordSpanModel,
    HarmonyModel,
    MetadataModel,
    NoteModel,
    QualityReportModel,
    RhythmModel,
    TrackModel,
)
from app.config import settings
from app.music.key_detection import KeyEstimate
from app.music.note_models import ChordSpan, Note
from app.pipeline.tempo_beats import TempoBeatResult

_PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_LOW_MODEL_SCORE_THRESHOLD = 0.35


def midi_number_to_note_name(midi_number: int) -> str:
    octave = midi_number // 12 - 1
    name = _PITCH_CLASS_NAMES[midi_number % 12]
    return f"{name}{octave}"


def note_to_model(note: Note) -> NoteModel:
    return NoteModel(
        pitch_midi=note.pitch_midi,
        note_name=midi_number_to_note_name(note.pitch_midi),
        onset_seconds_original=note.original.onset_seconds,
        offset_seconds_original=note.original.offset_seconds,
        duration_seconds_original=note.original.duration_seconds,
        onset_beat_raw=note.onset_beat_raw,
        duration_beats_raw=note.duration_beats_raw,
        onset_beat_quantized=note.onset_beat_quantized,
        duration_beats_quantized=note.duration_beats_quantized,
        onset_seconds_target=note.onset_seconds_target,
        offset_seconds_target=note.offset_seconds_target,
        model_score=note.model_amplitude,
        velocity_estimate=note.velocity_estimate,
        source_model=note.source_model,
        quantized=note.quantized,
        merged=note.merged,
    )


def build_track_model(track_type: str, notes: list[Note]) -> TrackModel:
    return TrackModel(
        track_type=track_type,
        note_count=len(notes),
        notes=[note_to_model(note) for note in notes],
    )


def chord_span_to_model(chord: ChordSpan) -> ChordSpanModel:
    return ChordSpanModel(
        start_time_seconds=chord.start_time_seconds,
        end_time_seconds=chord.end_time_seconds,
        chord=chord.chord_symbol,
        root=chord.root,
        bass=chord.bass,
        notes=chord.pitch_classes,
        confidence=chord.confidence,
    )


def _maximum_polyphony(notes: list[Note]) -> int:
    if not notes:
        return 0
    events = []
    for note in notes:
        events.append((note.original.onset_seconds, 1))
        events.append((note.original.offset_seconds, -1))
    events.sort(key=lambda e: (e[0], e[1]))
    current = 0
    peak = 0
    for _time, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def build_quality_report(full_notes: list[Note], warnings: list[str]) -> QualityReportModel:
    max_poly = _maximum_polyphony(full_notes)
    scores = [note.model_amplitude for note in full_notes]
    average_score = sum(scores) / len(scores) if scores else None
    low_score_count = sum(1 for s in scores if s < _LOW_MODEL_SCORE_THRESHOLD)

    manual_review = bool(warnings) or (average_score is not None and average_score < _LOW_MODEL_SCORE_THRESHOLD)

    return QualityReportModel(
        polyphonic=max_poly > 1,
        maximum_polyphony=max_poly,
        average_model_score=average_score,
        low_score_note_count=low_score_count,
        manual_review_recommended=manual_review,
        warnings=warnings,
    )


def build_analysis_result(
    *,
    original_filename: str,
    duration_seconds: float,
    sample_rate: int,
    channels: int,
    analysis_mode: str,
    target_bpm: float | None,
    quantization: str,
    tempo_result: TempoBeatResult,
    key_estimate: KeyEstimate | None,
    chords: list[ChordSpan],
    tracks: dict[str, list[Note]],
    warnings: list[str],
) -> AnalysisResult:
    full_notes = tracks.get("full", [])

    metadata = MetadataModel(
        filename=original_filename,
        duration_seconds=duration_seconds,
        sample_rate=sample_rate,
        channels=channels,
        analysis_mode=analysis_mode,
        pipeline_version=settings.PIPELINE_VERSION,
        target_bpm=target_bpm,
        quantization=quantization,
    )

    rhythm = RhythmModel(
        detected_bpm=tempo_result.detected_bpm,
        bpm_candidates=[BpmCandidateModel(bpm=c.bpm, score=c.score) for c in tempo_result.bpm_candidates],
        beat_times_seconds=[float(t) for t in tempo_result.beat_times],
        downbeat_times_seconds=tempo_result.downbeat_times,
        time_signature=tempo_result.time_signature,
        confidence=tempo_result.time_signature_confidence,
    )

    harmony = HarmonyModel(
        key=key_estimate.key_name if key_estimate else None,
        relative_key=key_estimate.relative_key_name if key_estimate else None,
        confidence=key_estimate.confidence if key_estimate else None,
        chords=[chord_span_to_model(c) for c in chords],
    )

    track_models = [build_track_model(track_type, notes) for track_type, notes in tracks.items()]
    quality_report = build_quality_report(full_notes, warnings)

    return AnalysisResult(
        metadata=metadata,
        rhythm=rhythm,
        harmony=harmony,
        tracks=track_models,
        quality_report=quality_report,
    )


def write_analysis_json(result: AnalysisResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
