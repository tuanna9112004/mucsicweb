class PipelineError(Exception):
    code = "PIPELINE_ERROR"
    http_status = 500

    def __init__(self, message: str):
        self.user_message = message
        super().__init__(message)


class NoFileSelectedError(PipelineError):
    code = "NO_FILE_SELECTED"
    http_status = 400


class UnsupportedFormatError(PipelineError):
    code = "UNSUPPORTED_FORMAT"
    http_status = 415


class FileUnreadableError(PipelineError):
    code = "FILE_UNREADABLE"
    http_status = 422


class FileTooLargeError(PipelineError):
    code = "FILE_TOO_LARGE"
    http_status = 413


class FileTooLongError(PipelineError):
    code = "FILE_TOO_LONG"
    http_status = 422


class FFmpegNotFoundError(PipelineError):
    code = "FFMPEG_NOT_FOUND"
    http_status = 503


class NoMelodyDetectedError(PipelineError):
    code = "NO_MELODY_DETECTED"
    http_status = 422


class AnalysisError(PipelineError):
    code = "ANALYSIS_ERROR"
    http_status = 500


class MidiExportError(PipelineError):
    code = "MIDI_EXPORT_FAILED"
    http_status = 500


class OutOfMemoryError(PipelineError):
    code = "OUT_OF_MEMORY"
    http_status = 507


class TaskCancelledError(PipelineError):
    code = "TASK_CANCELLED"
    http_status = 499


class JobNotFoundError(PipelineError):
    code = "JOB_NOT_FOUND"
    http_status = 404


class JobAlreadyRunningError(PipelineError):
    code = "JOB_ALREADY_RUNNING"
    http_status = 409


class JobResultNotReadyError(PipelineError):
    code = "JOB_RESULT_NOT_READY"
    http_status = 409
