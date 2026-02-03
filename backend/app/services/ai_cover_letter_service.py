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
        Creates/Updates placeholders for multiple questions and triggers the AI generation job.
        """
        # 1. Fetch Recruitment
        stmt = select(models.Recruitment).where(models.Recruitment.id == generate_req.recruit_id)
        result = await db.execute(stmt)
        recruitment = result.scalar_one_or_none()
        
        if not recruitment:
            raise ValueError("Recruitment not found")

        # 2. Get or Create Header Record
        if generate_req.cover_letter_id:
            # Check if exists and belongs to user
            from sqlalchemy.orm import selectinload
            stmt = (
                select(models.CoverLetter)
                .options(selectinload(models.CoverLetter.items))
                .where(
                    models.CoverLetter.id == generate_req.cover_letter_id,
                    models.CoverLetter.user_id == user_id
                )
            )
            result = await db.execute(stmt)
            cover_letter = result.scalar_one_or_none()
            if not cover_letter:
                raise ValueError("Existing cover letter not found or unauthorized")
            
            # Update existing
            cover_letter.processing_status = models.ProcessingStatus.PENDING
            cover_letter.content = "일괄 재작성 중입니다..."
            # Clear existing items (cascade will delete them)
            cover_letter.items = []
        else:
            cover_letter = models.CoverLetter(
                user_id=user_id,
                recruitment_id=recruitment.id,
                title=f"{recruitment.company} - {recruitment.title} 자소서 (생성 중)",
                content="일괄 작성 중입니다...",
                processing_status=models.ProcessingStatus.PENDING,
                gap_analysis={}
            )
            db.add(cover_letter)

        try:
            await db.flush() # Get ID if new

            # 3. Create Placeholder Items for each question
            for q_text in generate_req.questions:
                item = models.CoverLetterItem(
                    cover_letter_id=cover_letter.id,
                    question=q_text,
                    content="AI가 내용을 구성하고 있습니다...",
                    category="general"
                )
                db.add(item)
            
            await db.commit()
            await db.refresh(cover_letter)
        except Exception as e:
            logger.error(f"Failed to create/update cover letter placeholders: {e}")
            await db.rollback()
            raise e
        
        # 4. Trigger Job (Bulk)
        success = job_service.trigger_cover_letter_generation(
            cover_letter_id=cover_letter.id,
            tone=generate_req.tone,
            mode=generate_req.mode,
            portfolio_ids=generate_req.portfolio_ids,
            subheading=generate_req.subheading
        )
        
        if not success:
            logger.warning(f"Job trigger failed for cover letter {cover_letter.id}. Marking as FAILED.")
            try:
                cover_letter.processing_status = models.ProcessingStatus.FAILED
                await db.commit()
            except Exception as e_inner:
                logger.error(f"Failed to mark cover letter as FAILED: {e_inner}")
                await db.rollback()
        
        return cover_letter

ai_service = AICoverLetterService()
