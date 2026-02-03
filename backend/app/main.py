import logging
import sys
import threading
import shutil
import time
import os
from pathlib import Path
from contextlib import asynccontextmanager

# --- 1. Immediate STDOUT Debugging ---
print(f"STDOUT: main.py loading started at {time.time()}", flush=True)
print(f"STDOUT: PORT={os.environ.get('PORT', '8080')}", flush=True)

_start_time = time.time()

try:
    from fastapi import FastAPI, Request, status
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from common.config import settings
    from app.core.exceptions import AppBaseException
    print(f"STDOUT: Core libraries imported in {time.time() - _start_time:.2f}s", flush=True)
except Exception as e:
    print(f"STDOUT: CRITICAL ERROR during early imports: {e}", flush=True)
    sys.exit(1)

# --- 2. Logging Setup ---
from app.core.logging_utils import setup_structured_logging
setup_structured_logging()
logger = logging.getLogger("main")
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# --- 3. Background Tasks ---

def run_db_initialization():
    print("STDOUT: Background DB init starting...", flush=True)
    try:
        from common.db_init import init_db
        init_db()
        print("STDOUT: Background DB init complete.", flush=True)
    except Exception as e:
        print(f"STDOUT: Background DB init ERROR: {e}", flush=True)
        logger.error(f"Background: Database initialization failed: {e}")

def run_startup_cleanup():
    print("STDOUT: Background cleanup starting...", flush=True)
    try:
        upload_dir = Path("/tmp/uploads")
        if upload_dir.exists():
            for item in upload_dir.iterdir():
                try:
                    if item.is_file(): item.unlink()
                    elif item.is_dir(): shutil.rmtree(item)
                except Exception: pass
        else:
            upload_dir.mkdir(parents=True, exist_ok=True)
        print("STDOUT: Background cleanup complete.", flush=True)
    except Exception as e:
        print(f"STDOUT: Background cleanup ERROR: {e}", flush=True)

# --- 4. Router Logic (Moved inside lifespan for deferral) ---

_routers_included = False

def include_routers(app_obj: FastAPI):
    """Import and include routers with extreme diagnostic tracing."""
    global _routers_included
    if _routers_included:
        return
        
    print("STDOUT: Starting router inclusion process...", flush=True)
    _routers_total_start = time.time()
    
    def load_router(name, prefix, tags):
        s = time.time()
        print(f"DEBUG: Loading {name}...", flush=True)
        try:
            # Import inside function to keep startup minimal
            if name == "auth": from app.api.endpoints import auth as m
            elif name == "recruits": from app.api.endpoints import recruits as m
            elif name == "portfolios": from app.api.endpoints import portfolios as m
            elif name == "cover_letters": from app.api.endpoints import cover_letters as m
            elif name == "health": from app.api.endpoints import health as m
            elif name == "notifications": from app.api.endpoints import notifications as m
            elif name == "integrations": from app.api.endpoints import integrations as m
            elif name == "admin": from app.api.endpoints import admin as m
            else: return
            
            app_obj.include_router(m.router, prefix=prefix, tags=tags)
            print(f"STDOUT: Router '{name}' included in {time.time() - s:.3f}s", flush=True)
        except Exception as e:
            print(f"STDOUT: ERROR loading router '{name}': {e}", flush=True)

    load_router("auth", "/api/auth", ["Authentication"])
    load_router("recruits", "/api/recruits", ["Recruitments"])
    load_router("portfolios", "/api/portfolios", ["Portfolios"])
    load_router("cover_letters", "/api/cover-letters", ["Cover Letters"])
    load_router("health", "/api/health", ["System"])
    load_router("admin", "/api/admin", ["Admin"])
    load_router("notifications", "/api/notifications", ["Notifications"])
    load_router("integrations", "/api/integrations", ["Integrations"])

    print(f"STDOUT: All routers processed in {time.time() - _routers_total_start:.3f}s", flush=True)
    _routers_included = True

def custom_openapi():
    """Ensure all routers are included before generating the OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    # Force router inclusion so Swagger shows everything
    include_routers(app)
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("STDOUT: Lifespan starting. Port should be bound now.", flush=True)
    
    # 1. Include Routers (safely handled by global flag)
    include_routers(app)
    
    # 2. Fire off background tasks
    logger.info("Lifespan: Starting background workers...")
    threading.Thread(target=run_db_initialization, daemon=True).start()
    threading.Thread(target=run_startup_cleanup, daemon=True).start()
    
    print("STDOUT: Lifespan setup complete. Ready for traffic.", flush=True)
    yield
    logger.info("Lifespan: Shutting down...")

# --- 5. FastAPI App Definition ---

print("STDOUT: Initializing FastAPI app object...", flush=True)
_app_definition_start = time.time()

app = FastAPI(
    title="Pro-NLP AI Recruitment Platform API",
    description="Pro-NLP Backend",
    version="1.1.4",
    lifespan=lifespan
)

# Override the openapi method to use our custom one
app.openapi = custom_openapi

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://pro-nlp-finalproject-nlp-01.vercel.app",
    "https://pro-nlp-finalproject-nlp-01-pileuszu-nlp-01-final.vercel.app",
    "https://pro-nlp-finalproject-nlp-01-pileuszu.vercel.app",
]

if settings.FRONTEND_URL:
    # Support multiple origins separated by comma
    if "," in settings.FRONTEND_URL:
        extra_origins = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]
        origins.extend(extra_origins)
    else:
        origins.append(settings.FRONTEND_URL)

# Remove duplicates and empty strings
origins = list(set([o for o in origins if o]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://pro-nlp-finalproject-nlp-01-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base routes defined BEFORE anything else
@app.get("/api/ping")
async def api_ping():
    return {"status": "ok", "message": "ping", "timestamp": time.time()}

@app.get("/")
async def root_ping():
    return {
        "status": "ok",
        "message": "Backend is listening",
        "timestamp": time.time(),
        "version": "1.1.2"
    }

# Exception Handlers
@app.exception_handler(AppBaseException)
async def app_base_exception_handler(request: Request, exc: AppBaseException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "detail": exc.message})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"success": False, "detail": "Validation Error", "errors": exc.errors()})

print(f"STDOUT: FastAPI App initiation finished in {time.time() - _app_definition_start:.4f}s. Waiting for port bind.", flush=True)
