import logging
import sys

# Configure basic logging for startup
from app.core.logging_utils import setup_structured_logging
setup_structured_logging()
logger = logging.getLogger("main")

# Suppress pdfminer logs
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import AppBaseException
from common.config import settings

logger.info("Importing endpoints...")
from app.api.endpoints import auth, recruits, portfolios, cover_letters, health, notifications, integrations

logger.info("Initializing FastAPI app...")
app = FastAPI(
    title="Pro-NLP AI Recruitment Platform API",
    description="AI 기반 채용 플랫폼의 프론트엔드-백엔드 협업을 위한 표준 API 규격서입니다.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize Database EARLY
from common.db_init import init_db
init_db()

# Cleanup temporary files at startup
import shutil
from pathlib import Path
UPLOAD_DIR = Path("/tmp/uploads")
if UPLOAD_DIR.exists():
    logger.info(f"Cleaning up temporary directory: {UPLOAD_DIR}")
    for item in UPLOAD_DIR.iterdir():
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as e:
            logger.warning(f"Failed to delete {item}: {e}")
else:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# CORS configuration
origins = [
    "https://pro-nlp-finalproject-nlp-01-pileuszu-nlp-01-final.vercel.app",
    "https://pro-nlp-finalproject-nlp-01.vercel.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://pro-nlp-finalproject-nlp-01-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Pro-NLP Backend is running", "docs": "/docs"}

logger.info("FastAPI app READY for port binding.")

# Global Exception Handlers
@app.exception_handler(AppBaseException)
async def app_base_exception_handler(request: Request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.message,
            "data": exc.detail
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "detail": "입력값 검증에 실패했습니다.",
            "errors": exc.errors()
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception occurred: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "detail": "서버 내부 오류가 발생했습니다.",
            "message": str(exc) if settings.ENV != "production" else "Internal Server Error"
        },
    )

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["System"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
from app.api.endpoints import admin
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(recruits.router, prefix="/api/recruits", tags=["Recruitments"])
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"])
app.include_router(cover_letters.router, prefix="/api/cover-letters", tags=["Cover Letters"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])

