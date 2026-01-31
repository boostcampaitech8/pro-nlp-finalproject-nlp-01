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
            
            # Download from GCS if needed
            if source.startswith("gs://"):
                local_file_name = os.path.basename(source)
                local_path = os.path.join("/tmp/downloads", f"{uuid.uuid4()}_{local_file_name}")
                source = await gcs_utils.download_file(source, local_path)
                logger.info(f"Downloaded GCS file to {source} for processing")

            if p_type == "file":
                text = self.file_extractor.extract(source)
                # Cleanup local download
                if source != portfolio.source_url and os.path.exists(source):
                    try: os.remove(source)
                    except: pass
            elif p_type == "notion":
                text = self.notion_extractor.extract(source)
            elif p_type == "github":
                text = self.github_extractor.extract(source)
            else:
                text = ""

            if not text or text.startswith("[Error]") or "Error" in text[:20]:
                raise ValueError(f"Extraction failed: {text}")

            portfolio.content = self._sanitize_text(text)
            await self.db.commit()

            # 2. Refine (AI Pipeline)
            combined_result = await self.llm_refiner.extract_user_data_and_queries(text)
            user_data = combined_result.user_data
            projects = user_data.projects
            
            if not projects:
                portfolio.extracted_summary = user_data.profile.summary
                portfolio.extracted_job_title = user_data.profile.job_title
                portfolio.processing_status = ProcessingStatus.REVIEW_REQUIRED
                await NotificationService.create_and_notify(
                    db=self.db,
                    user_id=portfolio.user_id,
                    title="포트폴리오 분석 완료",
                    message=f"[{portfolio.project_name}] AI 분석이 완료되었습니다. 내용을 검토해 주세요.",
                    link=f"/my/portfolios/{portfolio.id}",
                    notification_type="PORTFOLIO_READY"
                )
                await self.db.commit()
            else:
                base_title = portfolio.title
                p0 = projects[0]
                
                # P0 Embedding
                desc0 = p0.description_for_embedding or ""
                embedding0 = None
                if desc0:
                    try:
                        embedding0 = await self.vector_store.get_embedding(desc0)
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for background project {p0.project_name}: {e}")

                portfolio.project_name = p0.project_name
                portfolio.period = p0.period
                portfolio.role = p0.role
                portfolio.description = p0.description_for_embedding
                portfolio.tech_stack = p0.tech_stack
                portfolio.extracted_summary = user_data.profile.summary
                portfolio.extracted_job_title = user_data.profile.job_title
                portfolio.processing_status = ProcessingStatus.REVIEW_REQUIRED
                portfolio.embedding = embedding0

                # 4. Save Portfolios
                await NotificationService.create_and_notify(
                    db=self.db,
                    user_id=portfolio.user_id,
                    title="포트폴리오 분석 완료",
                    message=f"[{portfolio.project_name}] AI 분석이 완료되었습니다. 내용을 검토해 주세요.",
                    link=f"/my/portfolios/{portfolio.id}",
                    notification_type="PORTFOLIO_READY"
                )
                
                # Add Job Queries for p0 to main portfolio
                for jq in p0.job_queries:
                    q_emb = None
                    try:
                        q_emb = await self.vector_store.get_embedding(jq.query)
                    except Exception as e:
                        logger.error(f"Failed to pre-embed job query: {e}")

                    portfolio.job_queries.append(
                        PortfolioJobQuery(
                            type=jq.type,
                            query_text=jq.query,
                            evidence=jq.evidence,
                            embedding=q_emb
                        )
                    )
                
                self.db.add(portfolio)
                
                # Create other projects as new portfolios
                new_portfolios = [portfolio]
                
                for proj in projects[1:]:
                    desc_proj = proj.description_for_embedding or ""
                    embedding_proj = None
                    if desc_proj:
                        try:
                            embedding_proj = await self.vector_store.get_embedding(desc_proj)
                        except Exception as e:
                            logger.error(f"Failed to generate embedding for background project {proj.project_name}: {e}")

                    new_p = Portfolio(
                        title=base_title + f" ({proj.project_name})",
                        type=portfolio.type,
                        source_url=portfolio.source_url,
                        content=text,
                        user_id=portfolio.user_id,
                        extracted_summary=user_data.profile.summary,
                        extracted_job_title=user_data.profile.job_title,
                        processing_status=ProcessingStatus.REVIEW_REQUIRED,
                        project_name=proj.project_name,
                        period=proj.period,
                        role=proj.role,
                        description=proj.description_for_embedding,
                        tech_stack=proj.tech_stack,
                        embedding=embedding_proj
                    )
                    
                    # Add queries for this project
                    for jq in proj.job_queries:
                         q_emb = None
                         try:
                             q_emb = await self.vector_store.get_embedding(jq.query)
                         except: pass
                         
                         new_p.job_queries.append(
                            PortfolioJobQuery(
                                type=jq.type,
                                query_text=jq.query,
                                evidence=jq.evidence,
                                embedding=q_emb
                            )
                         )

                    self.db.add(new_p)
                    new_portfolios.append(new_p)
                
                await self.db.commit()
                logger.info(f"Successfully processed portfolio {portfolio.id} split into {len(new_portfolios)} entries")

                # 5. Trigger Post-Processing
                from jobs.services.recruit_service import precompute_recommendations_for_portfolio

                for p in new_portfolios:
                    try:
                        await precompute_recommendations_for_portfolio(self.db, p.id)
                    except Exception as e:
                        logger.error(f"Post-processing (Recs) failed for {p.id}: {e}")

                    try:
                         await self._update_user_global_profile(
                            user_id=p.user_id,
                            project_name=p.project_name,
                            role=p.role or "",
                            tech_stack=", ".join(p.tech_stack) if p.tech_stack else "",
                            description=p.description or ""
                        )
                    except Exception as e:
                        logger.error(f"Post-processing (Profile) failed for {p.id}: {e}")

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
            
            # Download from GCS if needed
            if source.startswith("gs://"):
                local_file_name = os.path.basename(source)
                local_path = os.path.join("/tmp/downloads", f"analyze_{uuid.uuid4()}_{local_file_name}")
                source = await gcs_utils.download_file(source, local_path)
                logger.info(f"Downloaded GCS file (Analysis) to {source} for processing")

            if p_type == "file":
                text = self.file_extractor.extract(source)
                # Cleanup
                if source != portfolio.source_url and os.path.exists(source):
                    try: os.remove(source)
                    except: pass
            elif p_type == "notion":
                text = self.notion_extractor.extract(source)
            elif p_type == "github":
                text = self.github_extractor.extract(source)
            else:
                text = ""

            if not text or text.startswith("[Error]"):
                raise ValueError(f"Extraction failed: {text}")

            portfolio.content = self._sanitize_text(text)
            await self.db.commit()

            # 2. Refine (AI Pipeline)
            combined_result = await self.llm_refiner.extract_user_data_and_queries(text)
            user_data = combined_result.user_data
            projects = user_data.projects
            
            if projects:
                p0 = projects[0]
                portfolio.project_name = p0.project_name
                portfolio.period = p0.period
                portfolio.role = p0.role
                portfolio.description = p0.description_for_embedding
                portfolio.tech_stack = p0.tech_stack
                
                for jq in p0.job_queries:
                    portfolio.job_queries.append(
                        PortfolioJobQuery(
                            type=jq.type,
                            query_text=jq.query,
                            evidence=jq.evidence
                        )
                    )
            
            portfolio.extracted_summary = user_data.profile.summary
            portfolio.extracted_job_title = user_data.profile.job_title
            portfolio.processing_status = ProcessingStatus.REVIEW_REQUIRED
            
            await NotificationService.create_and_notify(
                db=self.db,
                user_id=portfolio.user_id,
                title="포트폴리오 분석 완료",
                message=f"[{portfolio.project_name or '새 포트폴리오'}] 분석이 완료되었습니다. 내용을 검토해 주세요.",
                link=f"/my/portfolios/{portfolio.id}",
                notification_type="PORTFOLIO_READY"
            )
            await self.db.commit()
            logger.info(f"Analysis completed for Portfolio {portfolio_id}")

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
