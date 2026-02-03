import argparse
import asyncio
import logging
import os
import sys
import time

# Ensure project root and 'jobs' are in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logger = logging.getLogger("run_job")

# Import actual tasks
try:
    from jobs.tasks.portfolio_task import process_portfolio, run_profile_update, run_portfolio_embedding
    from jobs.tasks.cover_letter_task import (
        process_cover_letter, 
        process_headline_generation, 
        process_item_refinement
    )
    from jobs.tasks.recruit_task import process_recruitments
except ImportError as e:
    logger.error(f"Failed to import tasks: {e}")
    sys.exit(1)

# Initialize Database - Create tables and heal enums
from common.db_init import init_db
init_db()

async def main():
    parser = argparse.ArgumentParser(description="Cloud Run Job Runner")
    parser.add_argument("--task", type=str, required=True, help="Task to run (portfolio_extraction, portfolio_analysis, etc.)")
    parser.add_argument("--id", type=int, help="Target record ID")
    
    args = parser.parse_args()
    
    logger.info(f"Executing task: {args.task} with ID: {args.id}")
    
    start_time = time.time()
    
    try:
        if args.task == "portfolio_extraction":
            if not args.id:
                logger.error("Portfolio ID is required for portfolio_extraction")
                return
            await process_portfolio(args.id)
            
        elif args.task == "profile_update":
            if not args.id:
                logger.error("Portfolio ID is required for profile_update")
                return
            await run_profile_update(args.id)
            
        elif args.task == "portfolio_embedding":
            if not args.id:
                logger.error("Portfolio ID is required for portfolio_embedding")
                return
            await run_portfolio_embedding(args.id)
            
        elif args.task == "portfolio_analysis":
            if not args.id:
                logger.error("Portfolio ID is required for portfolio_analysis")
                return
            # Reuse process_portfolio logic or a specialized one?
            # User wants "analysis" for preview.
            # We'll call a specific service method for this.
            from jobs.services.portfolio_service import PortfolioService
            from common.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                service = PortfolioService(db)
                await service.run_analysis_extraction(args.id)
            
        elif args.task == "cover_letter_generation":
            if not args.id:
                logger.error("Cover Letter ID is required for cover_letter_generation")
                return
            await process_cover_letter(args.id)
            
        elif args.task == "cover_letter_item_headline":
            if not args.id:
                logger.error("Item ID is required for cover_letter_item_headline")
                return
            await process_headline_generation(args.id)

        elif args.task == "cover_letter_item_refine":
            if not args.id:
                logger.error("Item ID is required for cover_letter_item_refine")
                return
            await process_item_refinement(args.id)
            
        elif args.task == "recruit_update":
            # Can be called with user_id to update recommendation for specific user,
            # or without ID for global update/scraping.
            await process_recruitments(user_id=args.id)
            
        elif args.task == "recruit_indexing":
            # This is often part of recruit_update, but can be separate if needed
            logger.info("Running dedicated indexing task...")
            from jobs.tasks.recruit_task import run_scraper
            # Scraper now manages its own DB sessions to prevent timeouts
            await run_scraper()
        else:
            logger.error(f"Unknown task: {args.task}")
            
        duration = time.time() - start_time
        logger.info(f"Task {args.task} completed in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Task {args.task} failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
