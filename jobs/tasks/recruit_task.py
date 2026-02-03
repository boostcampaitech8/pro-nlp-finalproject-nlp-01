import logging
import traceback
from sqlalchemy import select
from common.database import AsyncSessionLocal
from common.models import Portfolio, Recommendation, Recruitment, User
from jobs.services.recruit_service import (
    precompute_recommendations_for_portfolio, 
    global_rerank_recommendations, 
    bulk_precompute_recommendations
)
from jobs.core.recruit.crawler import RecruitmentCrawler
from jobs.core.recruit.indexer import RecruitIndexer
from datetime import datetime

logger = logging.getLogger("recruit_task")

async def process_recruitments(user_id: int = None):
    """
    Heavy task: 
    1. Update recommendations for user's latest portfolio.
    2. Global reranking.
    3. (Optional) Run scraper.
    """
    if user_id:
        async with AsyncSessionLocal() as db:
            try:
                # Find latest portfolio
                stmt = select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc()).limit(1)
                result = await db.execute(stmt)
                portfolio = result.scalar_one_or_none()
                
                if portfolio:
                    logger.info(f"Updating recommendations for User {user_id}, Portfolio {portfolio.id}")
                    await precompute_recommendations_for_portfolio(db, portfolio.id)
                    
                    logger.info(f"Running Global Rerank for User {user_id}")
                    await global_rerank_recommendations(db, user_id)
                else:
                    logger.info(f"No portfolio found for User {user_id}")
            except Exception as e:
                logger.error(f"Recommendation update failed for User {user_id}: {e}")
                logger.error(traceback.format_exc())
    else:
        # Run periodic processing for all users or run scraper
        logger.info("Running general recruitment update (Scraper + Bulk Recommendations)")
        
        # 1. Scraper logic (Manages its own sessions to prevent timeout)
        await run_scraper() 
        
        # 2. Bulk recommendations (Create a fresh session)
        async with AsyncSessionLocal() as db:
             await bulk_precompute_recommendations(db)

# Scraper logic with disconnected session management
async def run_scraper():
    """
    Runs the RecruitmentCrawler and saves results to the database.
    Process: Check Existing -> Crawl (No DB) -> Save New (New Session)
    """
    logger.info("Starting recruitment scraper process...")
    
    existing_links = set()
    
    # Phase 1: Fetch existing links (Short session)
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Recruitment.link)
            res = await db.execute(stmt)
            existing_rows = res.all()
            existing_links = {row.link for row in existing_rows if row.link}
            logger.info(f"Loaded {len(existing_links)} existing recruitment links to skip.")
    except Exception as e:
        logger.error(f"Failed to fetch existing recruitments: {e}")
        return

    # Phase 2: Crawl (Long running, NO DB CONNECTION)
    try:
        crawler = RecruitmentCrawler(target_pages=3) 
        # This takes 15+ mins, so we must NOT have an open DB session here
        results = await crawler.crawl_and_parse(exclude_links=existing_links)
        logger.info(f"Crawler returned {len(results)} items. Syncing with database...")
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        logger.error(traceback.format_exc())
        return

    # Phase 3: Save Results & Index (Use modernized indexer)
    if not results:
        logger.info("No new items to save.")
        return

    try:
        async with AsyncSessionLocal() as db:
            indexer = RecruitIndexer()
            added_count = await indexer.add_recruitments(db, results)
            logger.info(f"Sync complete. Added/Updated {added_count} items through indexer.")
    except Exception as e:
        logger.error(f"Database sync failed: {e}")
        logger.error(traceback.format_exc())
