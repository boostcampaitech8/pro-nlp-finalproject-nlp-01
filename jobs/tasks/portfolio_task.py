import logging
from common.database import AsyncSessionLocal
from jobs.services.portfolio_service import PortfolioService

logger = logging.getLogger("portfolio_task")

async def process_portfolio(portfolio_id: int):
    """
    Heavy task: Extract text, run LLM refinement, and update DB.
    Delegates entirely to PortfolioService.
    """
    logger.info(f"Starting Portfolio Processing for ID: {portfolio_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            service = PortfolioService(db)
            await service.process_portfolio_logic(portfolio_id)
            logger.info(f"Portfolio Task Completed for ID: {portfolio_id}")
        except Exception as e:
            logger.error(f"Portfolio Task Failed for ID {portfolio_id}: {e}")
            raise

async def run_profile_update(portfolio_id: int):
    """
    Task to update user's global profile (summary, job title) based on a specific portfolio.
    """
    logger.info(f"Starting Profile Update for Portfolio ID: {portfolio_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            service = PortfolioService(db)
            await service.update_user_profile_from_portfolio(portfolio_id)
            logger.info(f"Profile Update Task Completed for Portfolio ID: {portfolio_id}")
        except Exception as e:
            logger.error(f"Profile Update Task Failed for Portfolio ID {portfolio_id}: {e}")
            raise

