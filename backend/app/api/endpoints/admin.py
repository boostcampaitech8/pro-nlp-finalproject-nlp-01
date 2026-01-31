from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import List
from common.database import get_async_db
from common.config import settings

router = APIRouter()

@router.post("/crawl", status_code=202)
def trigger_crawling(background_tasks: BackgroundTasks, secret: str):
    """
    Trigger the recruitment crawling process in the background.
    Requires a secret key for basic security.
    """
    if secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    from app.services.job_service import job_service
    # Trigger the scraping job
    success = job_service.trigger_job(task="recruit_update")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger crawling job (Infrastructure error)")
        
    return {"message": "Crawling job triggered successfully"}

@router.delete("/clear", status_code=200)
async def clear_database(
    secret: str,
    db = Depends(get_async_db)  # Use dependency for session
):
    """
    Clear ALL database tables by DROPPING them and Re-creating them.
    This ensures schema updates (like JSON -> Vector) are applied.
    WARNING: This will delete everything!
    """
    # Security check
    if secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    try:
        from sqlalchemy import text
        from common.database import async_engine, Base
        import common.models # Ensure models are loaded

        # 1. Get all tables in the public schema except alembic_version and spatial_ref_sys
        get_tables_query = text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
              AND tablename <> 'alembic_version'
        """)
        result = await db.execute(get_tables_query)
        tables = [row[0] for row in result.all()]
        
        if tables:
            # 2. Drop tables with CASCADE
            for t in tables:
                await db.execute(text(f'DROP TABLE IF EXISTS public."{t}" CASCADE'))
            await db.commit()
        
        # 3. Re-create tables with updated schema
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        return {
            "message": "All database tables dropped and re-created successfully.",
            "dropped_tables": tables,
            "schema_updated": True
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset DB: {str(e)}")
