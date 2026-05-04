import logging
from common.database import AsyncSessionLocal
from jobs.services.ai_cover_letter_service import ai_cover_letter_service

logger = logging.getLogger("cover_letter_task")

async def process_cover_letter(cl_id: int):
    """
    Heavy task: Cover Letter Generation.
    Delegates entire logic to AICoverLetterService.
    """
    logger.info(f"Starting Cover Letter Generation for ID: {cl_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            await ai_cover_letter_service.process_cover_letter_generation(db, cl_id)
        except Exception as e:
            logger.error(f"Task Failed: {e}")
            raise

async def process_headline_generation(item_id: int):
    """
    Headline Generation for a specific item.
    """
    logger.info(f"Starting Headline Generation for Item ID: {item_id}")
    async with AsyncSessionLocal() as db:
        try:
            await ai_cover_letter_service.generate_headline_for_item(db, item_id)
        except Exception as e:
            logger.error(f"Headline Task Failed: {e}")
            raise

async def process_item_refinement(item_id: int):
    """
    Subheading Refinement for a specific item.
    """
    logger.info(f"Starting Subheading Refinement for Item ID: {item_id}")
    async with AsyncSessionLocal() as db:
        try:
            await ai_cover_letter_service.refine_cover_letter_item(db, item_id)
        except Exception as e:
            logger.error(f"Refinement Task Failed: {e}")
            raise

