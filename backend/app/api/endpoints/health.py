from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from common.database import get_db, get_async_db

router = APIRouter()

@router.get("")
@router.get("")
async def health_check(
    async_db: AsyncSession = Depends(get_async_db)
):
    """
    Check if the API, Async Database, and Cloud Storage are working.
    """
    results = {
        "status": "healthy",
        "async_db": "unknown",
        "storage": "unknown",
        "message": "API is up"
    }

    # 1. Database Check
    try:
        await async_db.execute(text("SELECT 1"))
        results["async_db"] = "connected"
    except Exception as e:
        results["async_db"] = f"failed: {str(e)}"
        results["status"] = "unhealthy"

    # 2. Cloud Storage Check (GCS)
    try:
        from common.gcs_utils import gcs_utils
        success = gcs_utils.check_connectivity() # Assuming we add this or simulate
        results["storage"] = "connected" if success else "disconnected"
        if not success:
            results["status"] = "degraded"
    except Exception as e:
        results["storage"] = f"failed: {str(e)}"
        if results["status"] == "healthy":
             results["status"] = "degraded"

    return results
