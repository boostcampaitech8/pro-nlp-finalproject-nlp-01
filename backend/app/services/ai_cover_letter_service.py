import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common import models
from common import schemas
from app.services.job_service import job_service

logger = logging.getLogger(__name__)

class AICoverLetterService:
    async def generate_cover_letter(
        self, 
        db: AsyncSession, 
        user_id: int, 
        generate_req: schemas.CoverLetterGenerateRequest
    ) -> models.CoverLetter:
        """
        Creates a placeholder and triggers the AI generation job.
        """
        # 1. Fetch Recruitment (needed for title)
        stmt = select(models.Recruitment).where(models.Recruitment.id == generate_req.recruitId)
        result = await db.execute(stmt)
        recruitment = result.scalar_one_or_none()
        
        if not recruitment:
            raise ValueError("Recruitment not found")

        # 2. Create Placeholder Record
        cover_letter = models.CoverLetter(
            user_id=user_id,
            recruitment_id=recruitment.id,
            title=f"{recruitment.company} - {recruitment.title} 자소서 (생성 중)",
            content="작성 중입니다...",
            processing_status=models.ProcessingStatus.PENDING,
            gap_analysis={}
        )
        db.add(cover_letter)
        await db.commit()
        await db.refresh(cover_letter)
        
        # 3. Trigger Job
        success = job_service.trigger_job(
            task="cover_letter_generation", 
            target_id=cover_letter.id,
            question=generate_req.question,
            tone=generate_req.tone
        )
        
        if not success:
            cover_letter.processing_status = models.ProcessingStatus.FAILED
            await db.commit()
            # We still return the object, but with FAILED status so polling sees it
        
        return cover_letter

ai_service = AICoverLetterService()
