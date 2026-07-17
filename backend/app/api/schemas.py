from typing import Literal

from pydantic import BaseModel, Field


class NoteModel(BaseModel):
    note: str
    midi_number: int
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float
    start_beat: float
    duration_beats: float
    velocity: int
    confidence: float
    quantized: bool
    start_beat_raw: float
    duration_beats_raw: float
    merged: bool


class AnalysisResult(BaseModel):
    original_filename: str
    duration_seconds: float
    detected_bpm: float
    target_bpm: int
    time_signature: str = "4/4"
    estimated_key: str | None = None
    quantization: Literal["none", "1/4", "1/8", "1/16"]
    note_count: int
    processing_status: Literal["completed", "failed"]
    pipeline_version: str = "1.0.0"
    analysis_method: dict
    warnings: list[str] = Field(default_factory=list)
    notes: list[NoteModel]


class AnalyzeRequest(BaseModel):
    target_bpm: int = Field(ge=135, le=140, default=138)
    quantize: Literal["none", "1/4", "1/8", "1/16"] = "none"
