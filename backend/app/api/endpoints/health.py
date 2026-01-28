from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db, get_async_db

router = APIRouter()

@router.get("/")
async def health_check(
    db: Session = Depends(get_db),
    async_db: AsyncSession = Depends(get_async_db)
):
    """
    Check if the API, Sync and Async Database connections are working.
    """
    results = {
        "status": "healthy",
        "sync_db": "unknown",
        "async_db": "unknown",
        "message": "API is up"
    }
    
    try:
        db.execute(text("SELECT 1"))
        results["sync_db"] = "connected"
    except Exception as e:
        results["sync_db"] = f"failed: {str(e)}"
        results["status"] = "unhealthy"

    try:
        await async_db.execute(text("SELECT 1"))
        results["async_db"] = "connected"
    except Exception as e:
        results["async_db"] = f"failed: {str(e)}"
        results["status"] = "unhealthy"

    return results
