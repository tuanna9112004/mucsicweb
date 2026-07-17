from pathlib import Path

from app.api.schemas import AnalysisResult, NoteModel
from app.config import settings
from app.pipeline.midi_export import note_confidence_to_velocity
from app.pipeline.note_models import Note

_PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_number_to_note_name(midi_number: int) -> str:
    octave = midi_number // 12 - 1
    name = _PITCH_CLASS_NAMES[midi_number % 12]
    return f"{name}{octave}"


def notes_to_note_models(notes: list[Note]) -> list[NoteModel]:
    return [
        NoteModel(
            note=midi_number_to_note_name(note.pitch_midi),
            midi_number=note.pitch_midi,
            start_time_seconds=note.start_time_seconds,
            end_time_seconds=note.end_time_seconds,
            duration_seconds=note.duration_seconds,
            start_beat=note.start_beat,
            duration_beats=note.duration_beats,
            velocity=note_confidence_to_velocity(note.confidence),
            confidence=note.confidence,
            quantized=note.quantized,
            start_beat_raw=note.start_beat_raw,
            duration_beats_raw=note.duration_beats_raw,
            merged=note.merged,
        )
        for note in notes
    ]


def build_analysis_result(
    *,
    original_filename: str,
    duration_seconds: float,
    detected_bpm: float,
    target_bpm: int,
    quantization: str,
    notes: list[Note],
    estimated_key: str | None = None,
    warnings: list[str] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        original_filename=original_filename,
        duration_seconds=duration_seconds,
        detected_bpm=detected_bpm,
        target_bpm=target_bpm,
        estimated_key=estimated_key,
        quantization=quantization,
        note_count=len(notes),
        processing_status="completed",
        pipeline_version=settings.PIPELINE_VERSION,
        analysis_method={
            "tempo_beat_detection": "librosa.beat.beat_track",
            "melody_extraction": "basic-pitch==0.4.0",
        },
        warnings=warnings or [],
        notes=notes_to_note_models(notes),
    )


def write_analysis_json(result: AnalysisResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
