import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from common.config import settings

# Setup basic logging
# logging.basicConfig(level=logging.INFO) # Removing to avoid interfering with app logger
logger = logging.getLogger(__name__)

# 1. Base URL Parsing
raw_url = settings.DATABASE_URL
url = None
try:
    if raw_url:
        url = make_url(raw_url)
        # Handle legacy 'postgres' driver name
        if url.drivername == "postgres":
            url = url.set(drivername="postgresql")
    else:
        logger.warning("DATABASE_URL is not set. Database features will fail.")
except Exception as e:
    logger.error(f"Failed to parse DATABASE_URL: {e}")
    # We will let the engines fail lazily later if url is None

# --- Private Engine & Session Singletons ---
_engine = None
_async_engine = None
_SessionLocal = None
_AsyncSessionLocal = None

def get_sync_engine():
    global _engine
    if _engine is None:
        if url is None:
            raise RuntimeError("Cannot create sync engine: DATABASE_URL is invalid or missing.")
        # SQLAlchemy sync engine needs a synchronous driver (e.g., 'postgresql://')
        # Even if settings.DATABASE_URL has '+asyncpg', we must strip it for the sync engine.
        sync_url = url
        if "postgresql+asyncpg" in sync_url.drivername:
            sync_url = sync_url.set(drivername="postgresql")
        elif sync_url.drivername == "postgres":
            sync_url = sync_url.set(drivername="postgresql")

        # Supabase Pooler (6543) needs sslmode=require
        if "supabase.com" in (sync_url.host or "") or "supabase.co" in (sync_url.host or ""):
            if sync_url.port == 6543:
                sync_url = sync_url.update_query_dict({"sslmode": "require"})

        logger.info(f"Sync engine target: {sync_url.host}:{sync_url.port}")
        _engine = create_engine(sync_url, poolclass=NullPool)
    return _engine

def get_async_engine():
    global _async_engine
    if _async_engine is None:
        if url is None:
            raise RuntimeError("Cannot create async engine: DATABASE_URL is invalid or missing.")
        # Use postgresql+asyncpg driver
        async_url = url.set(drivername="postgresql+asyncpg")

        # asyncpg does not use 'sslmode' query param, but 'ssl' in connect_args or query.
        query = dict(async_url.query)
        query.pop("sslmode", None)
        async_url = async_url.set(query=query)

        logger.info(f"Async engine target: {async_url.host}:{async_url.port}")

        async_connect_args = {"statement_cache_size": 0}
        if "supabase.com" in (async_url.host or "") or "supabase.co" in (async_url.host or ""):
            async_connect_args["ssl"] = "require"

        _async_engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10,
            connect_args=async_connect_args
        )
    return _async_engine

def get_sync_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_sync_engine())
    return _SessionLocal

def get_async_session_local():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(get_async_engine(), expire_on_commit=False)
    return _AsyncSessionLocal

# --- Exported Objects ---

Base = declarative_base()

def get_db():
    """Dependency for getting synchronous database session."""
    session_factory = get_sync_session_local()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Dependency for getting asynchronous database session."""
    session_factory = get_async_session_local()
    async with session_factory() as db:
        yield db

def __getattr__(name):
    """Dynamic resolution of engine and session factory to ensure lazy loading."""
    if name == "engine":
        return get_sync_engine()
    if name == "async_engine":
        return get_async_engine()
    if name == "SessionLocal":
        return get_sync_session_local()
    if name == "AsyncSessionLocal":
        return get_async_session_local()
    raise AttributeError(f"module {__name__} has no attribute {name}")
