from typing import Literal

from pydantic import BaseModel, Field


class NoteModel(BaseModel):
    pitch_midi: int
    note_name: str

    onset_seconds_original: float
    offset_seconds_original: float
    duration_seconds_original: float

    onset_beat_raw: float
    duration_beats_raw: float
    onset_beat_quantized: float
    duration_beats_quantized: float

    onset_seconds_target: float
    offset_seconds_target: float

    model_score: float
    velocity_estimate: int
    source_model: str

    quantized: bool
    merged: bool


class TrackModel(BaseModel):
    track_type: Literal["full", "melody", "bass", "monophonic_melody"]
    note_count: int
    notes: list[NoteModel]


class ChordSpanModel(BaseModel):
    start_time_seconds: float
    end_time_seconds: float
    chord: str
    root: str | None
    bass: str | None
    notes: list[str]
    confidence: float


class BpmCandidateModel(BaseModel):
    bpm: float
    score: float


class RhythmModel(BaseModel):
    detected_bpm: float | None
    bpm_candidates: list[BpmCandidateModel]
    beat_times_seconds: list[float]
    downbeat_times_seconds: list[float]
    time_signature: str | None
    confidence: float | None


class HarmonyModel(BaseModel):
    key: str | None
    relative_key: str | None
    confidence: float | None
    chords: list[ChordSpanModel]


class QualityReportModel(BaseModel):
    polyphonic: bool
    maximum_polyphony: int
    average_model_score: float | None
    low_score_note_count: int
    manual_review_recommended: bool
    warnings: list[str] = Field(default_factory=list)


class MetadataModel(BaseModel):
    filename: str
    duration_seconds: float
    sample_rate: int
    channels: int
    analysis_mode: Literal["piano_accurate", "melody_quick"]
    pipeline_version: str
    target_bpm: float | None
    quantization: Literal["none", "1/4", "1/8", "1/16", "1/8T", "1/16T"]


class AnalysisResult(BaseModel):
    schema_version: str = "2.0"
    metadata: MetadataModel
    rhythm: RhythmModel
    harmony: HarmonyModel
    tracks: list[TrackModel]
    quality_report: QualityReportModel


class AnalyzeRequest(BaseModel):
    analysis_mode: Literal["piano_accurate", "melody_quick"] = "piano_accurate"
    # None = giữ nguyên tempo gốc, không retime.
    target_bpm: float | None = Field(default=138, ge=60, le=220)
    quantize: Literal["none", "1/4", "1/8", "1/16", "1/8T", "1/16T"] = "none"


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    duration_seconds: float
    size_bytes: int


class HealthResponse(BaseModel):
    ffmpeg_found: bool
    ffprobe_found: bool
    piano_model_available: bool


class StepStatusModel(BaseModel):
    key: str
    label: str
    status: Literal["pending", "active", "done", "error"]


class ErrorInfoModel(BaseModel):
    code: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["uploaded", "running", "done", "error", "cancelled"]
    steps: list[StepStatusModel]
    progress_pct: int
    error: ErrorInfoModel | None = None
    result_summary: AnalysisResult | None = None
    processing_time_seconds: float | None = None
