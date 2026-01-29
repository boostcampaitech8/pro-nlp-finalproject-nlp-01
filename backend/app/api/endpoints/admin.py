from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import List
import os
from app.db.database import get_async_db

router = APIRouter()

async def run_crawler_script(db_session_factory):
    """Background task to run the crawler and index results."""
    import logging
    from app.core.recruit.indexer import RecruitIndexer
    from app.core.recruit.crawler import RecruitmentCrawler

    logger = logging.getLogger("crawler")
    logging.basicConfig(level=logging.INFO)

    try:
        logger.info("Starting recruitment crawler...")
        
        # Run crawler
        crawler = RecruitmentCrawler(target_pages=1)
        data = await crawler.crawl_and_parse()
        
        if not data:
            logger.warning("No data returned from crawler")
            return
        
        logger.info(f"Crawler returned {len(data)} items. Indexing to database...")
        
        # Index data
        async with db_session_factory() as db:
            indexer = RecruitIndexer()
            count = await indexer.add_recruitments(db, data)
            logger.info(f"Successfully indexed {count} items.")

    except Exception as e:
        logger.error(f"Crawler/Indexer Task Exception: {e}", exc_info=True)

@router.post("/crawl", status_code=202)
def trigger_crawling(background_tasks: BackgroundTasks, secret: str):
    """
    Trigger the recruitment crawling process in the background.
    Requires a secret key for basic security.
    """
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "nlp-final-admin-secret")
    
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    from app.db.database import AsyncSessionLocal
    background_tasks.add_task(run_crawler_script, AsyncSessionLocal)
    return {"message": "Crawling started in background"}

@router.delete("/clear", status_code=200)
async def clear_database(
    secret: str,
    db = Depends(get_async_db)  # Use dependency for session
):
    """
    Clear ALL database tables (users, portfolios, recruitments, cover letters, recommendations).
    WARNING: This will delete everything!
    """
    # Security check
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "nlp-final-admin-secret")
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    try:
        from sqlalchemy import text
        
        # Order matters due to foreign keys - delete children first
        # 1. Delete recommendations (references both portfolios and recruitments)
        await db.execute(text("DELETE FROM recommendations"))
        
        # 2. Delete cover_letters (references users and recruitments)
        await db.execute(text("DELETE FROM cover_letters"))
        
        # 3. Delete portfolio_job_queries (references portfolios)
        await db.execute(text("DELETE FROM portfolio_job_queries"))
        
        # 4. Delete portfolios (references users)
        await db.execute(text("DELETE FROM portfolios"))
        
        # 5. Delete recruitments (no dependencies)
        await db.execute(text("DELETE FROM recruitments"))
        
        # 6. Delete users (parent of portfolios and cover_letters)
        await db.execute(text("DELETE FROM users"))
        
        # 7. Clear vector embeddings (portfolio and recruitment)
        await db.execute(text("DELETE FROM langchain_pg_embedding"))
        await db.execute(text("DELETE FROM langchain_pg_collection"))
        
        await db.commit()
        
        return {
            "message": "All database tables cleared successfully.",
            "cleared_tables": [
                "recommendations",
                "cover_letters", 
                "portfolio_job_queries",
                "portfolios",
                "recruitments",
                "users",
                "langchain_pg_embedding",
                "langchain_pg_collection"
            ]
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear DB: {str(e)}")
