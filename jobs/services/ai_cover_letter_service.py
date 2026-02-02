import logging
import os
import json
import traceback
import asyncio
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common import models
from jobs.core.cover_letter.retriever import PGHybridRetriever
from jobs.core.cover_letter.generator import CoverLetterGenerator
from jobs.core.portfolio.storage.supabase_vector_store import SupabaseVectorStore
from jobs.core.cover_letter.config import SEARCH_TOP_K
from jobs.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class AICoverLetterService:
    """
    Orchestrator for Cover Letter Generation Job.
    Delegates retrieval to PGHybridRetriever and generation to CoverLetterGenerator.
    """
    def __init__(self):
        self.generator = CoverLetterGenerator()

    async def process_cover_letter_generation(self, db: AsyncSession, cl_id: int):
        """
        Full pipeline: Fetch data -> Retrieve Context -> Analyze Gap -> Generate Answer -> Save.
        """
        # 1. Fetch Cover Letter
        stmt = select(models.CoverLetter).where(models.CoverLetter.id == cl_id)
        result = await db.execute(stmt)
        cl = result.scalar_one_or_none()
        
        if not cl:
            logger.error(f"Cover Letter {cl_id} not found")
            return

        try:
            # 2. Fetch Recruitment
            recruitment = (await db.execute(select(models.Recruitment).where(models.Recruitment.id == cl.recruitment_id))).scalar_one_or_none()
            if not recruitment:
                raise ValueError("Recruitment not found")

            # 3. Initialize Retriever
            retriever = PGHybridRetriever(db, cl.user_id)
            await retriever.load_documents()

            # Prepare Query for Retrieval
            query_embedding = None
            if recruitment.embedding is not None:
                if isinstance(recruitment.embedding, str):
                    try:
                        query_embedding = json.loads(recruitment.embedding)
                    except: pass
                else:
                    query_embedding = recruitment.embedding

            query_text = f"{recruitment.company} {recruitment.title} {recruitment.required_qualifications or ''}"
            
            # 4. Retrieve Context
            relevant_docs = retriever.search(query_text, query_embedding, top_k=SEARCH_TOP_K)
            
            # 5. Format experiences with metadata (llm-pipeline 방식)
            context_text = generator._format_experiences(relevant_docs)

            # 6. Gap Analysis
            gap_result = self.generator.analyze_gap(context_text, query_text)
            cl.gap_analysis = gap_result
            await db.commit()


            # 6. Generate Answers for each Item
            tone = os.getenv("JOB_EXTRA_TONE", "professional")
            generation_mode = os.getenv("JOB_EXTRA_MODE", "full") # 'full' or 'outline'
            
            # Fetch items created as placeholders in the backend
            items_stmt = select(models.CoverLetterItem).where(models.CoverLetterItem.cover_letter_id == cl_id)
            items_res = await db.execute(items_stmt)
            items = items_res.scalars().all()
            
            if not items:
                # Fallback for old records or unexpected states
                logger.warning(f"No items found for cover letter {cl_id}, creating one from title")
                items = [models.CoverLetterItem(
                    cover_letter_id=cl.id,
                    question=cl.title,
                    category="general"
                )]
                db.add(items[0])
                await db.flush()

            # Track used experiences to avoid repetition across questions
            used_experiences = []

            for i, item in enumerate(items):
                logger.info(f"Generating ({generation_mode}) for item {item.id} ({i+1}/{len(items)}): {item.question[:30]}... (Tone: {tone})")
                
                # Add delay between requests to avoid Rate Limit (429)
                if i > 0:
                    delay = 3 + random.uniform(0, 2)
                    logger.info(f"Sleeping for {delay:.2f}s to respect rate limits...")
                    await asyncio.sleep(delay)

                retries = 3
                for attempt in range(retries):
                    try:
                        if generation_mode == "outline":
                            outline_data = self.generator.generate_outline(
                                company_name=recruitment.company,
                                job_title=recruitment.title,
                                question=item.question,
                                context=context_text,
                                gap_analysis=gap_result,
                                core_values=recruitment.company_description or "",
                                hint=item.hint or ""
                            )
                            # Save outline result
                            item.content = f"""**[개요 생성 결과]**
**한 줄 결론**: {outline_data.get('one_liner')}

**핵심 메시지**: {', '.join(outline_data.get('key_messages', []))}

**문단 구성 계획**:
"""
                            for plan in outline_data.get('paragraph_plans', []):
                                item.content += f"\n- **{plan.get('section_title')}**: {plan.get('paragraph_goal')}"
                                if plan.get('key_points'):
                                    item.content += f" ({', '.join(plan.get('key_points'))})"
                            
                            item.key_points = outline_data.get('key_messages')
                            item.suggested_improvements = outline_data.get('questions_for_user')
                            
                        else:
                            # Default Full Generation
                            answer_data = self.generator.generate_answer(
                                company_name=recruitment.company,
                                job_title=recruitment.title,
                                question=item.question,
                                context=context_text,
                                gap_analysis=gap_result,
                                tone=tone,
                                core_values=recruitment.company_description or "",
                                max_length=item.max_length or 1000,
                                used_experiences=used_experiences.copy(),
                                hint=item.hint or ""
                            )

                            item.content = answer_data.get("content")
                            item.key_points = answer_data.get("key_points")
                            item.suggested_improvements = answer_data.get("suggested_improvements")
                            
                            # Extract project names from content to track usage
                            # Simple heuristic: look for common project patterns
                            # This is a basic implementation - could be improved with NER
                            content = answer_data.get("content", "")
                            if "프로젝트" in content:
                                # Extract potential project names (very basic)
                                # In production, you might want more sophisticated parsing
                                pass
                        
                        # Update main cover letter content with the first item's content as a summary
                        if i == 0:
                            cl.content = item.content
                        
                        # Success, break retry loop
                        break

                    except Exception as e:
                        if "429" in str(e) or "Too Many Requests" in str(e):
                            if attempt < retries - 1:
                                wait_time = (2 ** attempt) * 5 + random.uniform(0, 3) 
                                logger.warning(f"Rate limit hit for item {item.id}. Retrying in {wait_time:.2f}s... (Attempt {attempt+1}/{retries})")
                                await asyncio.sleep(wait_time)
                                continue
                        
                        logger.error(f"Failed to generate for item {item.id}: {e}")
                        item.content = "이 문항에 대한 답변 생성에 실패했습니다."
                        break

            # Update Main Status
            cl.processing_status = models.ProcessingStatus.REVIEW_REQUIRED
            await db.commit()
            
            # 7. Create Notification
            await NotificationService.create_and_notify(
                db=db,
                user_id=cl.user_id,
                title="자기소개서 일괄 생성 완료",
                message=f"[{recruitment.company} - {recruitment.title}] 자기소개서의 모든 문항 작성이 완료되었습니다.",
                link=f"/my/cover-letters/{cl.id}",
                notification_type="COVER_LETTER_READY",
                target_id=cl.id
            )
            
            await db.commit() # Final commit
            
            logger.info(f"Successfully generated cover letter {cl_id}")

        except Exception as e:
            logger.error(f"Generation Failed for Cover Letter {cl_id}: {e}\n{traceback.format_exc()}")
            cl.processing_status = models.ProcessingStatus.FAILED
            await db.commit()
            raise


# Singleton instance
ai_cover_letter_service = AICoverLetterService()

