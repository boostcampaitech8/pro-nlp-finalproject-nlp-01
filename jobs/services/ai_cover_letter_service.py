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
            logger.info(f"Cover Letter {cl_id} not found or already deleted. Skipping job.")
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
            context_text = self.generator._format_experiences(relevant_docs)

            # 6. Gap Analysis
            gap_result = self.generator.analyze_gap(context_text, query_text)
            cl.gap_analysis = gap_result
            await db.commit()


            # 6. Generate Answers for each Item
            subheading_str = os.getenv("JOB_EXTRA_SUBHEADING", "false").lower()
            subheading = subheading_str == "true"
            tone = os.getenv("JOB_EXTRA_TONE", "professional")
            generation_mode = os.getenv("JOB_EXTRA_MODE", "full") # 'full' or 'outline'
            temperature = float(os.getenv("JOB_EXTRA_TEMPERATURE", "0.0"))
            
            # Fetch items created as placeholders in the backend, ordered by order_index
            items_stmt = (
                select(models.CoverLetterItem)
                .where(models.CoverLetterItem.cover_letter_id == cl_id)
                .order_by(models.CoverLetterItem.order_index.asc())
            )
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
            
            # Get all project names available in context for tracking
            available_projects = []
            for doc in relevant_docs:
                p_name = doc.metadata.get("project_name")
                if p_name and p_name not in available_projects:
                    available_projects.append(p_name)

            for i, item in enumerate(items):
                logger.info(f"Generating ({generation_mode}) for item {item.id} ({i+1}/{len(items)}): {item.question[:30]}... (Tone: {tone}, Subheading: {subheading}, Temp: {temperature})")
                
                # Add delay between requests to avoid Rate Limit (429)
                if i > 0:
                    delay = 5 + random.uniform(2, 5)
                    logger.info(f"Sleeping for {delay:.2f}s to respect rate limits...")
                    await asyncio.sleep(delay)

                try:
                    if generation_mode == "outline":
                        outline_data = self.generator.generate_outline(
                            company_name=recruitment.company,
                            job_title=recruitment.title,
                            question=item.question,
                            context=context_text,
                            gap_analysis=gap_result,
                            core_values=recruitment.company_description or ""
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

                            subheading=subheading,
                            temperature=temperature
                        )

                        item.content = answer_data.get("content")
                        
                        # Prepend Title as Subheading if requested or available
                        gen_title = answer_data.get("title")
                        if gen_title and subheading and not item.content.strip().startswith("["):
                             item.content = f"[{gen_title}]\n\n{item.content}"

                        item.key_points = answer_data.get("key_points")
                        item.suggested_improvements = answer_data.get("suggested_improvements")
                        
                        # Track which projects were likely used in this answer
                        content = answer_data.get("content", "")
                        for p_name in available_projects:
                            if p_name in content and p_name not in used_experiences:
                                used_experiences.append(p_name)
                    
                    # Update main cover letter content with the first item's content as a summary
                    if i == 0:
                        cl.content = item.content
            
                except Exception as e:
                    logger.error(f"Failed to generate for item {item.id} after internal retries: {e}")
                    item.content = "이 문항에 대한 답변 생성에 실패했습니다."

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
            
            # 8. Trigger UI Refresh
            await NotificationService.create_and_notify(
                db=db,
                user_id=cl.user_id,
                title="", message="",
                notification_type="REFRESH",
                target_id=cl.id
            )
            
            await db.commit() # Final commit
            
            logger.info(f"Successfully generated cover letter {cl_id}")

        except Exception as e:
            logger.error(f"Generation Failed for Cover Letter {cl_id}: {e}\n{traceback.format_exc()}")
            cl.processing_status = models.ProcessingStatus.FAILED
            await db.commit()
            raise

    async def refine_cover_letter_item(self, db: AsyncSession, item_id: int) -> models.CoverLetterItem:
        """
        Refines a specific cover letter item's content by adding subheadings.
        """
        stmt = select(models.CoverLetterItem).where(models.CoverLetterItem.id == item_id)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise ValueError(f"Cover Letter Item {item_id} not found")
            
        if not item.content:
            raise ValueError("Item has no content to refine")
            
        logger.info(f"Refining item {item_id} with subheadings...")
        refined_text = self.generator.refine_with_subheadings(item.content)
        
        item.content = refined_text
        await db.commit()
        await db.refresh(item)
        
        return item

    async def generate_headline_for_item(self, db: AsyncSession, item_id: int) -> models.CoverLetterItem:
        """
        Generates a headline for a specific cover letter item and prepends it.
        """
        stmt = select(models.CoverLetterItem).where(models.CoverLetterItem.id == item_id)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise ValueError(f"Cover Letter Item {item_id} not found")
            
        if not item.content:
            raise ValueError("Item has no content to generate headline")
            
        logger.info(f"Generating headline for item {item_id}...")
        headline = self.generator.generate_headline(item.content)
        
        # Prepend headline if it doesn't look like it's already there
        # Check if first line looks like a bracketed title
        lines = item.content.split('\n')
        if lines and lines[0].strip().startswith('[') and lines[0].strip().endswith(']'):
             # Replace existing headline
             lines[0] = f"[{headline}]"
             item.content = '\n'.join(lines)
        else:
             # Prepend
             item.content = f"[{headline}]\n\n{item.content}"
        
        await db.commit()
        await db.refresh(item)
        
        return item


# Singleton instance
ai_cover_letter_service = AICoverLetterService()

