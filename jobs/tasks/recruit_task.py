import os
import logging
import asyncio
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

    # Combined Phase 2 & 3: Stream Crawl -> Refine -> Embed -> Save (Incremental)
    try:
        # Read pages and limit from environment
        target_pages = int(os.getenv("JOB_EXTRA_PAGES", "3"))
        crawl_limit = os.getenv("JOB_EXTRA_LIMIT")
        crawl_limit = int(crawl_limit) if crawl_limit else None
        
        logger.info(f"Starting crawler (incremental): target_pages={target_pages}, limit={crawl_limit}")
        crawler = RecruitmentCrawler(target_pages=target_pages)
        indexer = RecruitIndexer()
        
        # Process each item immediately as it is parsed
        processed_count = 0
        async with AsyncSessionLocal() as db:
            async for item in crawler.crawl_and_parse_gen(exclude_links=existing_links, limit=crawl_limit):
                try:
                    # Indexer handles embedding and individual commit
                    await indexer.add_recruitments(db, [item])
                    processed_count += 1
                    if processed_count % 5 == 0:
                        logger.info(f"Progress: Processed {processed_count} items...")
                except Exception as item_e:
                    logger.error(f"Failed to index individual item: {item_e}")
                    continue

        logger.info(f"Incremental sync complete. Total items added/updated: {processed_count}")
    except Exception as e:
        logger.error(f"Incremental crawler task failed: {e}")
        logger.error(traceback.format_exc())

async def run_fix_questions(limit: int = 20):
    """
    Identifies recruitments with malformed questions (Korean keys) and fixes them
    by re-crawling and re-parsing.
    """
    logger.info(f"Starting question fix task (limit={limit})...")
    
    from jobs.core.recruit.crawler import RecruitmentCrawler
    from jobs.core.recruit.scrapers.saramin import SaraminScraper
    import urllib.parse
    
    crawler = RecruitmentCrawler()
    
    async with AsyncSessionLocal() as db:
        # Fetch candidates: Check recent ones first
        stmt = select(Recruitment).where(Recruitment.questions.isnot(None)).order_by(Recruitment.id.desc()).limit(limit * 10)
        result = await db.execute(stmt)
        candidates = result.scalars().all()
        
        fixed_count = 0
        
        for recruit in candidates:
            if fixed_count >= limit:
                break
                
            questions = recruit.questions
            if not questions:
                continue
                
            # Check if malformed (has Korean key '질문')
            is_malformed = False
            for q in questions:
                if isinstance(q, dict) and '질문' in q:
                    is_malformed = True
                    break
            
            if not is_malformed:
                continue
                
            logger.info(f"Fixing Recruitment {recruit.id} ({recruit.title})...")
            
            content_text = ""
            image_urls = []
            
            try:
                # 1. Fetch Content
                if recruit.link and "saramin.co.kr" in recruit.link:
                    scraper = SaraminScraper()
                    parsed = urllib.parse.urlparse(recruit.link)
                    qs = urllib.parse.parse_qs(parsed.query)
                    rec_idx = qs.get('rec_idx', [None])[0]
                    
                    if rec_idx:
                        content_text, image_urls = await scraper.get_job_details(rec_idx)
                
                if not content_text and recruit.link:
                    # Fallback to generic crawler
                    # get_job_detail is a sync method, run in executor
                    loop = asyncio.get_event_loop()
                    content_text, images_str, _ = await loop.run_in_executor(None, crawler.get_job_detail, recruit.link)
                    image_urls = images_str.split(", ") if images_str else []
                
                if not content_text:
                    logger.warning(f"Failed to fetch content for {recruit.id}")
                    continue
                    
                # 2. Re-parse with LLM (Strict Schema)
                job_data = {
                    'company': recruit.company,
                    'title': recruit.title,
                    'url': recruit.link,
                    'apply_url': recruit.link,
                    'content_text': content_text,
                    'content_images': ", ".join(image_urls)
                }
                
                loop = asyncio.get_event_loop()
                items = await loop.run_in_executor(None, crawler._analyze_job_with_ncp, job_data)
                
                if items:
                    # Take the first item's questions
                    # We only update questions, avoiding overwrite of other manual fields if any
                    new_questions = items[0].get('questions')
                    if new_questions:
                        # Convert to dict if they are Pydantic models (should already be dicts from crawler)
                        recruit.questions = new_questions
                        db.add(recruit)
                        await db.commit()
                        logger.info(f"-> Fixed questions for {recruit.id}")
                        fixed_count += 1
                    else:
                        logger.warning(f"-> LLM returned no questions for {recruit.id}")
                else:
                    logger.warning(f"-> LLM returned no items for {recruit.id}")
            
            except Exception as e:
                logger.error(f"Error fixing {recruit.id}: {e}")
                continue
                
        logger.info(f"Question fix task complete. Fixed {fixed_count} items.")

async def run_deduplicate_questions():
    """
    Iterates through all recruitment records and deduplicates their questions.
    """
    logger.info("Starting global recruitment question deduplication...")
    
    async with AsyncSessionLocal() as db:
        stmt = select(Recruitment).where(Recruitment.questions.isnot(None))
        result = await db.execute(stmt)
        recruitments = result.scalars().all()
        
        updated_count = 0
        total_count = len(recruitments)
        
        for recruit in recruitments:
            questions = recruit.questions
            if not questions or not isinstance(questions, list):
                continue
                
            seen_texts = set()
            new_questions = []
            has_duplicates = False
            
            for q in questions:
                if not isinstance(q, dict):
                    continue
                    
                q_text = q.get('question', '').strip()
                if not q_text:
                    continue
                    
                if q_text not in seen_texts:
                    seen_texts.add(q_text)
                    new_questions.append(q)
                else:
                    has_duplicates = True
            
            if has_duplicates:
                recruit.questions = new_questions
                db.add(recruit)
                updated_count += 1
                
                if updated_count % 10 == 0:
                    await db.commit()
                    logger.info(f"Progress: Deduplicated {updated_count} records so far...")
        
        await db.commit()
    
    logger.info(f"Question deduplication complete. Updated {updated_count} out of {total_count} records.")
