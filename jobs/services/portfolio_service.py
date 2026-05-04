import os
import logging
import httpx
import uuid
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common.models import Portfolio, PortfolioJobQuery, PortfolioChunk, ProcessingStatus
from common import schemas
from common.gcs_utils import gcs_utils
from jobs.services.notification_service import NotificationService
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._file_extractor = None
        self._notion_extractor = None
        self._github_extractor = None
        self._blog_extractor = None # Added
        self._llm_refiner = None
        self._vector_store = None
        
    def _sanitize_text(self, text: str) -> str:
        """Removes null bytes and other characters that cause DB storage issues."""
        if not text:
            return ""
        return text.replace("\x00", "")

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 160) -> List[str]:
        """Splits text into chunks with overlap."""
        if not text:
            return []
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
            
            # Prevent infinite loop if overlap >= chunk_size
            if start >= len(text) or chunk_size <= overlap:
                break
        return chunks

    async def _calculate_and_save_chunks(self, portfolio: Portfolio, text: str):
        """Splits text into chunks, gets embeddings, and saves to DB."""
        if not text:
            return
        
        # Clear existing chunks
        portfolio.chunks = []
        
        chunks = self._chunk_text(text, chunk_size=800, overlap=160)
        for idx, chunk_text in enumerate(chunks):
            c_emb = None
            try:
                c_emb = await self.vector_store.get_embedding(chunk_text)
            except Exception as e:
                logger.error(f"Chunk embedding failed for portfolio {portfolio.id} chunk {idx}: {e}")
            
            portfolio.chunks.append(
                PortfolioChunk(
                    chunk_content=chunk_text,
                    embedding=c_emb,
                    chunk_index=idx
                )
            )
        logger.info(f"Successfully saved {len(chunks)} chunks for portfolio {portfolio.id}")

    @property
    def file_extractor(self):
        if not self._file_extractor:
            from jobs.core.portfolio.extractors.file_extractor import FileExtractor
            self._file_extractor = FileExtractor()
        return self._file_extractor

    @property
    def notion_extractor(self):
        if not self._notion_extractor:
            from jobs.core.portfolio.extractors.notion_extractor import NotionExtractor
            self._notion_extractor = NotionExtractor()
        return self._notion_extractor

    @property
    def github_extractor(self):
        if not self._github_extractor:
            from jobs.core.portfolio.extractors.github_extractor import GitHubExtractor
            self._github_extractor = GitHubExtractor()
        return self._github_extractor

    @property
    def llm_refiner(self):
        if not self._llm_refiner:
            from jobs.core.portfolio.processors.llm_refiner import LLMRefiner
            self._llm_refiner = LLMRefiner()
        return self._llm_refiner

    @property
    def vector_store(self):
        if not self._vector_store:
            from jobs.core.portfolio.storage.supabase_vector_store import SupabaseVectorStore
            self._vector_store = SupabaseVectorStore()
        return self._vector_store

    @property
    def blog_extractor(self):
        if not self._blog_extractor:
            from jobs.core.portfolio.extractors.blog_extractor import BlogExtractor
            self._blog_extractor = BlogExtractor()
        return self._blog_extractor

    async def process_portfolio_logic(self, portfolio_id: int):
        """
        Core logic for processing a portfolio.
        """
        try:
            # Fetch Portfolio with queries and chunks
            stmt = (
                select(Portfolio)
                .where(Portfolio.id == portfolio_id)
                .options(
                    selectinload(Portfolio.job_queries),
                    selectinload(Portfolio.chunks)
                )
            )
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                logger.info(f"Portfolio {portfolio_id} not found or already deleted. Skipping job.")
                return

            portfolio.processing_status = ProcessingStatus.PROCESSING
            await self.db.commit()

            # 1. Extract
            source = portfolio.source_url
            p_type = portfolio.type
            
            extracted_projects = [] # List of {"title": str, "content": str, "url": str}

            # Download from GCS if needed
            if source.startswith("gs://"):
                local_file_name = os.path.basename(source)
                local_path = os.path.join("/tmp/downloads", f"{uuid.uuid4()}_{local_file_name}")
                source = await gcs_utils.download_file(source, local_path)
                logger.info(f"Downloaded GCS file to {source} for processing")

            # 0. Get User Integration (Token) if available
            from common.models import UserIntegration
            stmt_int = select(UserIntegration).where(
                UserIntegration.user_id == portfolio.user_id, 
                UserIntegration.provider == p_type
            )
            res_int = await self.db.execute(stmt_int)
            integration = res_int.scalar_one_or_none()
            token = integration.access_token if integration else None

            if p_type == "file":
                text = self.file_extractor.extract(source)
                # Cleanup local download
                if source != portfolio.source_url and os.path.exists(source):
                    try: os.remove(source)
                    except: pass
            elif p_type == "notion":
                # Notion
                if token:
                    from notion_client import Client
                    self.notion_extractor.client = Client(auth=token)
                notion_title, text = await self.notion_extractor._process_node(source)
                
                # If project name is placeholder/empty, update it with extracted title
                if notion_title and (not portfolio.project_name or "Notion" in portfolio.project_name or "Analysis" in portfolio.project_name):
                    portfolio.project_name = notion_title
                    await self.db.commit()
            elif p_type == "text":
                text = portfolio.content or ""
                logger.info("Processing manual text input directly.")
            elif p_type == "github":
                extracted_projects = self.github_extractor.extract_multi(source, token=token)
            elif p_type == "blog":
                extracted_projects = await self.blog_extractor.extract_multi(source)
            else:
                raise ValueError(f"Unknown portfolio type: {p_type}")

            # AI-powered split for multi-project documents (file, notion, text)
            if p_type in ["file", "notion", "text"]:
                logger.info(f"Using AI to detect multiple projects in {p_type} content...")
                combined = await self.llm_refiner.extract_user_data_and_queries(text)
                
                if combined.user_data.projects:
                    logger.info(f"AI detected {len(combined.user_data.projects)} projects in single {p_type} source.")
                    extracted_projects = []
                    for i, p in enumerate(combined.user_data.projects):
                        extracted_projects.append({
                            "title": p.project_name or (f"{p_type} Project {i+1}"),
                            "content": text, # Pass original text for refining if needed
                            "url": portfolio.source_url,
                            "refined_data": p # Carry over refined data
                        })
                else:
                    extracted_projects = [{"title": portfolio.project_name or "New Portfolio", "content": text, "url": portfolio.source_url}]

            if not extracted_projects:
                raise ValueError(f"Extraction failed or no projects found for {p_type}")

            # 2. Pre-create records for all projects to get IDs and show progress in UI
            project_records_meta = []
            for i, proj_data in enumerate(extracted_projects):
                proj_url = proj_data["url"]
                proj_title = proj_data["title"] or (f"{p_type} Project {i+1}")
                
                if i == 0:
                    portfolio.project_name = proj_title
                    portfolio.source_url = proj_url
                    target = portfolio
                else:
                    target = Portfolio(
                        user_id=portfolio.user_id,
                        type=portfolio.type,
                        source_url=proj_url,
                        project_name=proj_title,
                        processing_status=ProcessingStatus.PROCESSING
                    )
                    self.db.add(target)
                
                target.content = proj_data["content"] # Save raw content for re-analysis
                project_records_meta.append({"id": None, "target": target, "data": proj_data})
            
            await self.db.flush()
            for item in project_records_meta:
                item["id"] = item["target"].id
            
            await self.db.commit()
            await self.db.commit()
            logger.info(f"Pre-created {len(project_records_meta)} portfolio records. Starting LLM refinement...")

            # DEBUG: Log extracted text for debugging missing fields
            for i, p_meta in enumerate(project_records_meta):
                content_preview = (p_meta['data']['content'] or "")[:200].replace("\n", " ")
                logger.info(f"[DEBUG] Project {i} Content Length: {len(p_meta['data']['content'] or '')} chars. Sample: {content_preview}...")

            # 3. Process each project with LLM
            import asyncio
            for i, item in enumerate(project_records_meta):
                # Add delay to prevent rate limiting in batch processing
                if i > 0:
                    await asyncio.sleep(1.0)
                
                target_id = item["id"]
                proj_data = item["data"]
                proj_text = proj_data["content"]
                proj_title = proj_data["title"]

                # Re-fetch the portfolio record to avoid expired object issues after commit
                stmt = (
                    select(Portfolio)
                    .where(Portfolio.id == target_id)
                    .options(
                        selectinload(Portfolio.job_queries),
                        selectinload(Portfolio.chunks)
                    )
                )
                res = await self.db.execute(stmt)
                target_portfolio = res.scalar_one()

                # Refine single project
                if "refined_data" in proj_data:
                    logger.info(f"Using pre-refined data for project {i}: {proj_title}")
                    project_refined = proj_data["refined_data"]
                else:
                    project_refined = await self.llm_refiner.refine_single_project(proj_text, project_name_hint=proj_title)

                # Update portfolio data
                target_portfolio.project_name = project_refined.project_name
                target_portfolio.period = project_refined.period
                target_portfolio.role = project_refined.role
                target_portfolio.description = project_refined.description_for_embedding
                target_portfolio.content = proj_text  # SAVE RAW CONTENT
                target_portfolio.tech_stack = project_refined.tech_stack
                target_portfolio.strengths = [s.model_dump() for s in project_refined.strengths]
                
                # Add Job Queries

                # Add Job Queries
                # Clear existing if any (for i=0)
                if i == 0:
                    target_portfolio.job_queries = []
                
                for jq in project_refined.job_queries:
                    q_emb = None
                    try:
                        q_emb = await self.vector_store.get_embedding(jq.query)
                    except: pass
                    
                    target_portfolio.job_queries.append(
                        PortfolioJobQuery(
                            type=jq.type,
                            query_text=jq.query,
                            evidence=jq.evidence,
                            embedding=q_emb
                        )
                    )

                # Calculate and save chunks with embeddings
                await self._calculate_and_save_chunks(target_portfolio, target_portfolio.description)

                target_portfolio.processing_status = ProcessingStatus.REVIEW_REQUIRED
                await self.db.commit()

                # Notify
                await NotificationService.create_and_notify(
                    db=self.db,
                    user_id=target_portfolio.user_id,
                    title="포트폴리오 분석 완료",
                    message=f"[{target_portfolio.project_name}] AI 분석이 완료되었습니다. 내용을 검토해 주세요.",
                    link=f"/my/portfolios/{target_portfolio.id}",
                    notification_type="PORTFOLIO_READY",
                    target_id=target_portfolio.id
                )

                # Post-processing (Recommendations)
                try:
                    from jobs.services.recruit_service import precompute_recommendations_for_portfolio
                    await precompute_recommendations_for_portfolio(self.db, target_portfolio.id)
                except Exception as e:
                    logger.error(f"Post-processing (Recs) failed for {target_portfolio.id}: {e}")

                # Update user global profile incrementally
                try:
                    await self._update_user_global_profile(
                        user_id=target_portfolio.user_id,
                        project_name=target_portfolio.project_name,
                        role=target_portfolio.role or "",
                        tech_stack=", ".join(target_portfolio.tech_stack) if target_portfolio.tech_stack else "",
                        description=target_portfolio.description or ""
                    )
                except Exception as e:
                    logger.error(f"Post-processing (Profile) failed for {target_portfolio.id}: {e}")

            logger.info(f"Successfully processed {len(extracted_projects)} portfolios from {source}")

        except Exception as e:
            logger.error(f"Processing Failed for Portfolio {portfolio_id}: {e}")
            await self.db.rollback()
            try:
                stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
                result = await self.db.execute(stmt)
                portfolio = result.scalar_one_or_none()
                if portfolio:
                    portfolio.processing_status = ProcessingStatus.FAILED
                    await self.db.commit()
            except Exception as final_e:
                logger.error(f"Final failure state update failed: {final_e}")
            raise

    async def _update_user_global_profile(self, user_id: int, project_name: str, role: str, tech_stack: str, description: str):
        
        # Define internal function to be retried
        @retry(
            retry=retry_if_exception_type(Exception), # Broad retry for DB conflicts, could be more specific (e.g. OperationalError)
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=5)
        )
        async def _execute_update():
            from common.models import User
            # Use with_for_update() to lock the user row and prevent race conditions
            stmt = select(User).where(User.id == user_id).with_for_update()
            res = await self.db.execute(stmt)
            user = res.scalar_one_or_none()
            
            if not user: return

            new_info = f"프로젝트명: {project_name}\n역할: {role}\n기술스택: {tech_stack}\n내용: {description}"
            
            updated_profile = await self.llm_refiner.update_global_user_profile(
                current_summary=user.profile_summary or "",
                current_job_title=user.desired_job_title or "",
                new_project_info=new_info
            )
            
            user.profile_summary = updated_profile.get("summary", user.profile_summary)
            user.desired_job_title = updated_profile.get("job_title", user.desired_job_title)
            
            await self.db.commit()
            logger.info(f"Updated global profile for User {user_id}")
        
        try:
            await _execute_update()
        except Exception as e:
            logger.error(f"Failed to update global profile for user {user_id} after retries: {e}")
            await self.db.rollback()

    async def update_user_profile_from_portfolio(self, portfolio_id: int):
        """
        Public method to trigger profile update from a specific portfolio.
        Used by the 'profile_update' task.
        """
        try:
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                logger.error(f"Portfolio {portfolio_id} not found for profile update")
                return

            await self._update_user_global_profile(
                user_id=portfolio.user_id,
                project_name=portfolio.project_name,
                role=portfolio.role or "",
                tech_stack=", ".join(portfolio.tech_stack) if portfolio.tech_stack else "",
                description=portfolio.description or ""
            )
        except Exception as e:
            logger.error(f"Profile update task failed for portfolio {portfolio_id}: {e}")
            raise

    async def run_analysis_extraction(self, portfolio_id: int):
        """
        Specialized task for 'Preview/Analysis' only.
        """
        try:
            stmt = (
                select(Portfolio)
                .where(Portfolio.id == portfolio_id)
                .options(
                    selectinload(Portfolio.job_queries),
                    selectinload(Portfolio.chunks)
                )
            )
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                logger.error(f"Portfolio {portfolio_id} not found for analysis")
                return

            portfolio.processing_status = ProcessingStatus.PROCESSING
            await self.db.commit()

            # 1. Extract
            source = portfolio.source_url
            p_type = portfolio.type
            
            extracted_projects = [] # List of {"title": str, "content": str, "url": str}

            # Download from GCS if needed
            if source.startswith("gs://"):
                local_file_name = os.path.basename(source)
                local_path = os.path.join("/tmp/downloads", f"analyze_{uuid.uuid4()}_{local_file_name}")
                source = await gcs_utils.download_file(source, local_path)
                logger.info(f"Downloaded GCS file (Analysis) to {source} for processing")

            # 0. Get User Integration (Token) if available
            from common.models import UserIntegration
            stmt_int = select(UserIntegration).where(
                UserIntegration.user_id == portfolio.user_id, 
                UserIntegration.provider == p_type
            )
            res_int = await self.db.execute(stmt_int)
            integration = res_int.scalar_one_or_none()
            token = integration.access_token if integration else None

            if p_type == "text" or (portfolio.content and not source.startswith("http")):
                # USE EXISTING CONTENT FOR RE-ANALYSIS
                text = portfolio.content
            elif p_type == "file":
                text = self.file_extractor.extract(source)
                # Cleanup
                if source != portfolio.source_url and os.path.exists(source):
                    try: os.remove(source)
                    except: pass
            elif p_type == "notion":
                # If we have a token from integration, use it. Otherwise use default.
                if token:
                    from notion_client import Client
                    self.notion_extractor.client = Client(auth=token)
                notion_title, text = await self.notion_extractor._process_node(source)
                if notion_title and (not portfolio.project_name or "Notion" in portfolio.project_name):
                    portfolio.project_name = notion_title
            elif p_type == "github":
                extracted_projects = self.github_extractor.extract_multi(source, token=token)
            elif p_type == "blog":
                extracted_projects = await self.blog_extractor.extract_multi(source)
            else:
                raise ValueError(f"Unknown portfolio type: {p_type}")

            # AI-powered split for multi-project documents (file, notion, text)
            if p_type in ["file", "notion", "text"] or (p_type == "text" or (portfolio.content and not source.startswith("http"))):
                if not extracted_projects: # Only if not already extracted (e.g. from file)
                    logger.info(f"Using AI to detect multiple projects in {p_type} content (Analysis)...")
                    combined = await self.llm_refiner.extract_user_data_and_queries(text)
                    
                    if combined.user_data.projects:
                        logger.info(f"AI detected {len(combined.user_data.projects)} projects in single {p_type} source (Analysis).")
                        extracted_projects = []
                        for i, p in enumerate(combined.user_data.projects):
                            extracted_projects.append({
                                "title": p.project_name or (f"{p_type} Project {i+1}"),
                                "content": text,
                                "url": portfolio.source_url,
                                "refined_data": p
                            })
                    else:
                        extracted_projects = [{"title": portfolio.project_name or "New Portfolio", "content": text, "url": portfolio.source_url}]

            if not extracted_projects:
                raise ValueError(f"Extraction failed or no projects found for {p_type}")

            # 2. Pre-create records for all projects to get IDs and show progress in UI
            project_records_meta = []
            for i, proj_data in enumerate(extracted_projects):
                proj_url = proj_data["url"]
                proj_title = proj_data["title"] or (f"{p_type} Project {i+1}")
                
                if i == 0:
                    portfolio.project_name = proj_title
                    portfolio.source_url = proj_url
                    target = portfolio
                else:
                    target = Portfolio(
                        user_id=portfolio.user_id,
                        type=portfolio.type,
                        source_url=proj_url,
                        project_name=proj_title,
                        processing_status=ProcessingStatus.PROCESSING
                    )
                    self.db.add(target)
                
                target.content = proj_data["content"] # Save raw content
                project_records_meta.append({"id": None, "target": target, "data": proj_data})
            
            await self.db.flush()
            for item in project_records_meta:
                item["id"] = item["target"].id
            
            await self.db.commit()
            await self.db.commit()
            logger.info(f"Pre-created {len(project_records_meta)} portfolio records (Analysis). Starting...")

            # DEBUG: Log extracted text for debugging missing fields
            for i, p_meta in enumerate(project_records_meta):
                content_preview = (p_meta['data']['content'] or "")[:200].replace("\n", " ")
                logger.info(f"[DEBUG] Analysis Project {i} Content Length: {len(p_meta['data']['content'] or '')} chars. Sample: {content_preview}...")

            # 3. Process each project with LLM
            import asyncio
            for i, item in enumerate(project_records_meta):
                # Add delay to prevent rate limiting in batch processing
                if i > 0:
                    await asyncio.sleep(1.0)
                
                target_id = item["id"]
                proj_data = item["data"]
                proj_text = proj_data["content"]
                proj_title = proj_data["title"]

                # Re-fetch the portfolio record
                stmt = (
                    select(Portfolio)
                    .where(Portfolio.id == target_id)
                    .options(
                        selectinload(Portfolio.job_queries),
                        selectinload(Portfolio.chunks)
                    )
                )
                res = await self.db.execute(stmt)
                target_portfolio = res.scalar_one()

                if i == 0:
                    # For the first one, we extract profile AND project data
                    combined_result = await self.llm_refiner.extract_user_data_and_queries(proj_text)
                    user_data = combined_result.user_data
                    
                    if user_data.projects:
                        project_refined = user_data.projects[0]
                    else:
                        # Fallback if AI didn't find specific projects in first chunk
                        project_refined = await self.llm_refiner.refine_single_project(proj_text, project_name_hint=proj_title)
                else:
                    # Refine single project
                    project_refined = await self.llm_refiner.refine_single_project(proj_text, project_name_hint=proj_title)

                # Update portfolio data
                target_portfolio.project_name = project_refined.project_name
                target_portfolio.period = project_refined.period
                target_portfolio.role = project_refined.role
                target_portfolio.description = project_refined.description_for_embedding
                target_portfolio.content = proj_text  # SAVE RAW CONTENT
                target_portfolio.tech_stack = project_refined.tech_stack
                target_portfolio.strengths = [s.model_dump() for s in project_refined.strengths]
                
                # Add Job Queries

                # Add Job Queries
                # Clear existing if any (for i=0)
                if i == 0:
                    target_portfolio.job_queries = []
                
                for jq in project_refined.job_queries:
                    q_emb = None
                    try:
                        q_emb = await self.vector_store.get_embedding(jq.query)
                    except: pass
                    
                    target_portfolio.job_queries.append(
                        PortfolioJobQuery(
                            type=jq.type,
                            query_text=jq.query,
                            evidence=jq.evidence,
                            embedding=q_emb
                        )
                    )
                
                # Calculate and save chunks with embeddings (Missing logic added)
                await self._calculate_and_save_chunks(target_portfolio, target_portfolio.description)

                target_portfolio.processing_status = ProcessingStatus.REVIEW_REQUIRED
                await self.db.commit()

                # Notify
                await NotificationService.create_and_notify(
                    db=self.db,
                    user_id=target_portfolio.user_id,
                    title="포트폴리오 분석 완료",
                    message=f"[{target_portfolio.project_name or '새 포트폴리오'}] 분석이 완료되었습니다. 내용을 검토해 주세요.",
                    link=f"/my/portfolios/{target_portfolio.id}",
                    notification_type="PORTFOLIO_READY",
                    target_id=target_portfolio.id
                )

                # Trigger UI Refresh - Use meaningful title for the background link
                await NotificationService.create_and_notify(
                    db=self.db,
                    user_id=target_portfolio.user_id,
                    title="REFRESH_TRIGGER", message=f"Portfolio {target_portfolio.id} processing update",
                    notification_type="REFRESH",
                    target_id=target_portfolio.id
                )

            logger.info(f"Analysis multi-process completed for {len(extracted_projects)} projects from {source}")

        except Exception as e:
            logger.error(f"Analysis extraction failed for Portfolio {portfolio_id}: {e}")
            await self.db.rollback()
            try:
                stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
                result = await self.db.execute(stmt)
                portfolio = result.scalar_one_or_none()
                if portfolio:
                    portfolio.processing_status = ProcessingStatus.FAILED
                    await self.db.commit()
            except Exception as final_e:
                logger.error(f"Final failure state update failed (Analysis): {final_e}")
            raise
    async def refresh_analysis_keeping_content(self, portfolio_id: int):
        """
        Refreshes only the AI-generated parts (Strengths, Job Queries, Embeddings)
        based on the CURRENT project description/content.
        This preserves the user's manual edits to Project Name, Period, Role, Stack, etc.
        """
        logger.info(f"Refreshing AI analysis (Strengths/Queries/Embeddings) for portfolio {portfolio_id}")
        
        stmt = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(
                selectinload(Portfolio.job_queries),
                selectinload(Portfolio.chunks)
            )
        )
        res = await self.db.execute(stmt)
        portfolio = res.scalar_one_or_none()
        
        if not portfolio:
            logger.error(f"Portfolio {portfolio_id} not found for refresh")
            return

        portfolio.processing_status = ProcessingStatus.PROCESSING
        await self.db.commit()

        try:
            # 1. Regenerate Strengths & Queries using LLM
            # We use description_for_embedding (which the user sees as 'content' in edit mode usually)
            # or 'content' if description is empty.
            target_text = portfolio.description or portfolio.content or ""
            
            if len(target_text) > 50:
                refined_data = await self.llm_refiner.refine_strengths_and_queries(
                    project_name=portfolio.project_name, 
                    description=target_text
                )
                
                # Update Strengths
                if refined_data.get("strengths"):
                    # Basic validation/cleaning could go here
                    portfolio.strengths = refined_data["strengths"]
                
                # Update Job Queries
                if refined_data.get("job_queries"):
                    # Clear old ones
                    from sqlalchemy import delete
                    await self.db.execute(delete(PortfolioJobQuery).where(PortfolioJobQuery.portfolio_id == portfolio_id))
                    
                    portfolio.job_queries = []
                    for jq in refined_data["job_queries"]:
                        q_emb = None
                        try:
                            q_emb = await self.vector_store.get_embedding(jq['query'])
                        except: pass
                        
                        portfolio.job_queries.append(
                            PortfolioJobQuery(
                                type=jq['type'],
                                query_text=jq['query'],
                                evidence=jq.get('evidence', []),
                                embedding=q_emb
                            )
                        )
            
            # 2. Re-calculate Chunks & Embeddings (Standard Procedure)
            await self._calculate_and_save_chunks(portfolio, target_text)

            portfolio.processing_status = ProcessingStatus.COMPLETED
            await self.db.commit()
            
            # 3. Notify
            await NotificationService.create_and_notify(
                db=self.db,
                user_id=portfolio.user_id,
                title="AI 분석 업데이트 완료",
                message=f"[{portfolio.project_name}] 수정된 내용을 바탕으로 AI 분석(강점/채용공고 매칭)이 갱신되었습니다.",
                link=f"/my/portfolios/{portfolio.id}",
                notification_type="REFRESH",
                target_id=portfolio.id
            )
            
            # 4. Trigger Recommendations
            try:
                from jobs.services.recruit_service import precompute_recommendations_for_portfolio
                await precompute_recommendations_for_portfolio(self.db, portfolio_id)
            except Exception as e:
                logger.error(f"Failed to update recs for portfolio {portfolio_id}: {e}")

            logger.info(f"Portfolio {portfolio_id} AI refresh completed.")

        except Exception as e:
            logger.error(f"Failed to refresh analysis for portfolio {portfolio_id}: {e}")
            await self.db.rollback()
            # Set back to COMPLETED or REVIEW_REQUIRED? safest is likely what it was, but easier to just say COMPLETED with error logged
            # Or FAILED if critical. Let's try to restore status potentially.
            # For now, just mark FAILED so user knows.
            portfolio.processing_status = ProcessingStatus.FAILED
            await self.db.commit()
            raise
