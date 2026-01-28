import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    load_dotenv()
except Exception:
    pass

from sqlalchemy.pool import NullPool

raw_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pro_nlp_db")

# Handle legacy 'postgres://' prefix
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

# Enforce sslmode=require for Supabase Pooler (port 6543) if not present
if "supabase.com:6543" in raw_url and "sslmode=" not in raw_url:
    separator = "&" if "?" in raw_url else "?"
    raw_url += f"{separator}sslmode=require"

DATABASE_URL = raw_url
# Use a safer logging that won't crash if URL is weird
try:
    url_tag = DATABASE_URL.split('@')[-1].split('?')[0]
except Exception:
    url_tag = "unknown"
logger.info(f"Initializing database engines... (Target: {url_tag})")

# Sync Engine
engine = create_engine(DATABASE_URL, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async Engine
# Ensure we don't double-replace if it already has a driver specified
if "postgresql+asyncpg://" not in DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

logger.info(f"Async engine target: {ASYNC_DATABASE_URL.split('@')[-1].split('?')[0]}")

# asyncpg handles SSL differently (via connect_args or 'ssl' param)
async_connect_args = {"statement_cache_size": 0}
if "supabase.com" in ASYNC_DATABASE_URL:
    async_connect_args["ssl"] = "require"

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=NullPool,
    connect_args=async_connect_args
)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
