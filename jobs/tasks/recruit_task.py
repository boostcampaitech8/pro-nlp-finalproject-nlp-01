import logging
import traceback
from sqlalchemy import select
from common.database import AsyncSessionLocal
from common.models import Portfolio, Recommendation, Recruitment, User
from jobs.services.recruit_service import precompute_recommendations_for_portfolio, global_rerank_recommendations
from jobs.core.recruit.crawler import RecruitmentCrawler
from datetime import datetime

logger = logging.getLogger("recruit_task")

import logging
import traceback
from sqlalchemy import select
from common.database import AsyncSessionLocal
from common.models import Portfolio, Recommendation, Recruitment, User
from jobs.services.recruit_service import precompute_recommendations_for_portfolio, global_rerank_recommendations, bulk_precompute_recommendations
from jobs.core.recruit.crawler import RecruitmentCrawler
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
    
    existing_identifiers = set()
    
    # Phase 1: Fetch existing IDs (Short session)
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Recruitment.company, Recruitment.title)
            res = await db.execute(stmt)
            existing_rows = res.all()
            existing_identifiers = {(row.company, row.title) for row in existing_rows}
            logger.info(f"Loaded {len(existing_identifiers)} existing recruitments to skip.")
    except Exception as e:
        logger.error(f"Failed to fetch existing recruitments: {e}")
        return

    # Phase 2: Crawl (Long running, NO DB CONNECTION)
    try:
        crawler = RecruitmentCrawler(target_pages=3) 
        # This takes 15+ mins, so we must NOT have an open DB session here
        results = await crawler.crawl_and_parse(exclude_identifiers=existing_identifiers)
        logger.info(f"Crawler returned {len(results)} items. Syncing with database...")
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        logger.error(traceback.format_exc())
        return

    # Phase 3: Save Results (New Short session)
    if not results:
        logger.info("No new items to save.")
        return

    try:
        async with AsyncSessionLocal() as db:
            new_count = 0
            updated_count = 0
            
            for item in results:
                # Check for existing recruitment by link
                # (We check link again here to be safe and update existing records)
                stmt = select(Recruitment).where(Recruitment.link == item['link'])
                res = await db.execute(stmt)
                existing = res.scalar_one_or_none()
                
                # Helper to parse dates
                def parse_date(date_str):
                    if not date_str or date_str == "상시채용":
                        return None
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        return None
    
                if existing:
                    # Update existing record
                    existing.title = item.get('title', existing.title)
                    existing.company = item.get('company', existing.company)
                    existing.deadline = parse_date(item.get('deadline')) or existing.deadline
                    existing.location = item.get('location', existing.location)
                    existing.experience = item.get('experience', existing.experience)
                    existing.education = item.get('education', existing.education)
                    existing.employment_type = item.get('employment_type', existing.employment_type)
                    existing.salary = item.get('salary', existing.salary)
                    existing.category = item.get('category', existing.category)
                    existing.key_responsibilities = item.get('key_responsibilities', existing.key_responsibilities)
                    existing.required_qualifications = item.get('required_qualifications', existing.required_qualifications)
                    existing.preferred_qualifications = item.get('preferred_qualifications', existing.preferred_qualifications)
                    existing.tags = item.get('tags', existing.tags)
                    updated_count += 1
                else:
                    # Create new record
                    new_rec = Recruitment(
                        title=item.get('title'),
                        company=item.get('company'),
                        link=item.get('link'),
                        start_date=parse_date(item.get('start_date')),
                        deadline=parse_date(item.get('deadline')),
                        location=item.get('location'),
                        experience=item.get('experience'),
                        education=item.get('education'),
                        employment_type=item.get('employment_type'),
                        salary=item.get('salary'),
                        category=item.get('category'),
                        key_responsibilities=item.get('key_responsibilities'),
                        required_qualifications=item.get('required_qualifications'),
                        preferred_qualifications=item.get('preferred_qualifications'),
                        tags=item.get('tags')
                    )
                    db.add(new_rec)
                    new_count += 1
            
            await db.commit()
            logger.info(f"Sync complete. New: {new_count}, Updated: {updated_count}")

    except Exception as e:
        logger.error(f"Database sync failed: {e}")
        logger.error(traceback.format_exc())
