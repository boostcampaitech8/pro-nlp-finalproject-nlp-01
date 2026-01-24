from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth, recruits, portfolios, cover_letters, health

app = FastAPI(
    title="Pro-NLP AI Recruitment Platform API",
    description="AI 기반 채용 플랫폼의 프론트엔드-백엔드 협업을 위한 표준 API 규격서입니다.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Pro-NLP AI Recruitment Platform API", "docs": "/docs"}

# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "입력값 검증에 실패했습니다.",
            "errors": exc.errors()
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "서버 내부 오류가 발생했습니다.",
            "message": str(exc)
        },
    )

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["System"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(recruits.router, prefix="/api/recruits", tags=["Recruitments"])
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"])
app.include_router(cover_letters.router, prefix="/api/cover-letters", tags=["Cover Letters"])

