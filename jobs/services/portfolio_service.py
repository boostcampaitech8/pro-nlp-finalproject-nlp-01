import os
import logging
import httpx
import uuid
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common.models import Portfolio, PortfolioJobQuery, ProcessingStatus
from common import schemas
from common.gcs_utils import gcs_utils
from jobs.services.notification_service import NotificationService

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
            # Fetch Portfolio with queries
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id).options(selectinload(Portfolio.job_queries))
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                logger.error(f"Portfolio {portfolio_id} not found")
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
                extracted_projects = [{"title": portfolio.project_name or "New File", "content": text, "url": portfolio.source_url}]
                # Cleanup local download
                if source != portfolio.source_url and os.path.exists(source):
                    try: os.remove(source)
                    except: pass
            elif p_type == "notion":
                # If we have a token from integration, use it. Otherwise use default.
                if token:
                    self.notion_extractor.client = None # Reset to re-init with new token
                    self.notion_extractor.access_token = token
                    from notion_client import Client
                    self.notion_extractor.client = Client(auth=token)
                
                text = self.notion_extractor.extract(source)
                extracted_projects = [{"title": portfolio.project_name or "Notion Page", "content": text, "url": source}]
            elif p_type == "github":
                extracted_projects = self.github_extractor.extract_multi(source, token=token)
            elif p_type == "blog":
                extracted_projects = await self.blog_extractor.extract_multi(source)
            else:
                raise ValueError(f"Unknown portfolio type: {p_type}")

            if not extracted_projects:
                raise ValueError(f"Extraction failed or no projects found for {p_type}")

            # 2. Process each extracted project
            # First one updates the existing portfolio, others create new ones
            for i, proj_data in enumerate(extracted_projects):
                proj_text = proj_data["content"]
                proj_title = proj_data["title"]
                proj_url = proj_data["url"]

                # Refine single project (more accurate & cost effective)
                # If only one project was extracted, we can use the old method which extracts profile too, 
                # but for batch, we use refine_single_project.
                project_refined = await self.llm_refiner.refine_single_project(proj_text, project_name_hint=proj_title)
                
                target_portfolio = None
                if i == 0:
                    target_portfolio = portfolio
                else:
                    # Create a new portfolio record for subsequent projects
                    target_portfolio = Portfolio(
                        user_id=portfolio.user_id,
                        type=portfolio.type,
                        source_url=proj_url,
                        processing_status=ProcessingStatus.PROCESSING
                    )
                    self.db.add(target_portfolio)
                    await self.db.flush() # Get ID

                # Update portfolio data
                target_portfolio.project_name = project_refined.project_name
                target_portfolio.period = project_refined.period
                target_portfolio.role = project_refined.role
                target_portfolio.description = project_refined.description_for_embedding
                target_portfolio.tech_stack = project_refined.tech_stack
                target_portfolio.content = self._sanitize_text(proj_text)
                
                # Generate embedding
                if target_portfolio.description:
                    try:
                        target_portfolio.embedding = await self.vector_store.get_embedding(target_portfolio.description)
                    except Exception as e:
                        logger.error(f"Embedding failed for {target_portfolio.id}: {e}")

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
        try:
            from common.models import User
            stmt = select(User).where(User.id == user_id)
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
            
        except Exception as e:
            logger.error(f"Failed to update global profile for user {user_id}: {e}")

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
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id).options(selectinload(Portfolio.job_queries))
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

            if p_type == "file":
                text = self.file_extractor.extract(source)
                extracted_projects = [{"title": portfolio.project_name or "New File", "content": text, "url": portfolio.source_url}]
                # Cleanup
                if source != portfolio.source_url and os.path.exists(source):
                    try: os.remove(source)
                    except: pass
            elif p_type == "notion":
                # If we have a token from integration, use it. Otherwise use default.
                if token:
                    self.notion_extractor.client = None
                    self.notion_extractor.access_token = token
                    from notion_client import Client
                    self.notion_extractor.client = Client(auth=token)
                text = self.notion_extractor.extract(source)
                extracted_projects = [{"title": portfolio.project_name or "Notion Page", "content": text, "url": source}]
            elif p_type == "github":
                extracted_projects = self.github_extractor.extract_multi(source, token=token)
            elif p_type == "blog":
                extracted_projects = await self.blog_extractor.extract_multi(source)
            else:
                raise ValueError(f"Unknown portfolio type: {p_type}")

            if not extracted_projects:
                raise ValueError(f"Extraction failed or no projects found for {p_type}")

            # 2. Process each extracted project
            # First one updates the existing portfolio, others create new ones
            for i, proj_data in enumerate(extracted_projects):
                proj_text = proj_data["content"]
                proj_title = proj_data["title"]
                proj_url = proj_data["url"]

                target_portfolio = None
                if i == 0:
                    target_portfolio = portfolio
                    # For the first one, we extract profile AND project data
                    combined_result = await self.llm_refiner.extract_user_data_and_queries(proj_text)
                    user_data = combined_result.user_data
                    
                    target_portfolio.extracted_summary = user_data.profile.summary
                    target_portfolio.extracted_job_title = user_data.profile.job_title
                    
                    if user_data.projects:
                        project_refined = user_data.projects[0]
                    else:
                        # Fallback if AI didn't find specific projects in first chunk
                        project_refined = await self.llm_refiner.refine_single_project(proj_text, project_name_hint=proj_title)
                else:
                    # Create a new portfolio record for subsequent projects
                    target_portfolio = Portfolio(
                        user_id=portfolio.user_id,
                        type=portfolio.type,
                        source_url=proj_url,
                        processing_status=ProcessingStatus.PROCESSING
                    )
                    self.db.add(target_portfolio)
                    await self.db.flush() # Get ID
                    
                    # Refine single project
                    project_refined = await self.llm_refiner.refine_single_project(proj_text, project_name_hint=proj_title)

                # Update portfolio data
                target_portfolio.project_name = project_refined.project_name
                target_portfolio.period = project_refined.period
                target_portfolio.role = project_refined.role
                target_portfolio.description = project_refined.description_for_embedding
                target_portfolio.tech_stack = project_refined.tech_stack
                target_portfolio.content = self._sanitize_text(proj_text)
                
                # Generate embedding
                if target_portfolio.description:
                    try:
                        target_portfolio.embedding = await self.vector_store.get_embedding(target_portfolio.description)
                    except Exception as e:
                        logger.error(f"Embedding failed for {target_portfolio.id}: {e}")

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
