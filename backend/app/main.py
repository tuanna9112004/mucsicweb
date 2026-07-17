import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_download, routes_health, routes_jobs, routes_upload
from app.core.errors import PipelineError

logger = logging.getLogger(__name__)

app = FastAPI(title="Melody Tempo Analyzer")

app.include_router(routes_health.router)
app.include_router(routes_upload.router)
app.include_router(routes_jobs.router)
app.include_router(routes_download.router)


@app.exception_handler(PipelineError)
def handle_pipeline_error(request: Request, exc: PipelineError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.user_message}},
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Lỗi không mong muốn khi xử lý request %s", request.url)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "ANALYSIS_ERROR",
                "message": "Đã xảy ra lỗi không mong muốn ở server.",
            }
        },
    )


# Frontend (Stage 5) được phục vụ dưới dạng static files — mount cuối cùng để
# không che các route /api/* đã đăng ký ở trên. Thư mục có thể chưa tồn tại
# trong các stage trước đó nên cần guard bằng exists().
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
