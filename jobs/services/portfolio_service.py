import os
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common.models import Portfolio, PortfolioJobQuery, ProcessingStatus
from common import schemas

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._file_extractor = None
        self._notion_extractor = None
        self._github_extractor = None
        self._llm_refiner = None
        self._vector_store = None

    @property
    def file_extractor(self):
        if not self._file_extractor:
            from common.extractors.file_extractor import FileExtractor
            self._file_extractor = FileExtractor()
        return self._file_extractor

    @property
    def notion_extractor(self):
        if not self._notion_extractor:
            from common.extractors.notion_extractor import NotionExtractor
            self._notion_extractor = NotionExtractor()
        return self._notion_extractor

    @property
    def github_extractor(self):
        if not self._github_extractor:
            from common.extractors.github_extractor import GitHubExtractor
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
        Core logic for processing a portfolio:
        1. Extract text based on type
        2. Refine with LLM (extract projects)
        3. Save projects as separate Portfolio records (if multiple) or update existing
        4. Generate embeddings
        5. Trigger subsequent updates
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
            
            if p_type == "file":
                text = self.file_extractor.extract(source)
            elif p_type == "notion":
                text = self.notion_extractor.extract(source)
            elif p_type == "github":
                text = self.github_extractor.extract(source)
            else:
                text = ""

            if not text or text.startswith("[Error]") or "Error" in text[:20]:
                raise ValueError(f"Extraction failed: {text}")

            portfolio.content = text
            await self.db.commit()

            # 2. Refine (AI Pipeline)
            combined_result = await self.llm_refiner.extract_user_data_and_queries(text)
            user_data = combined_result.user_data
            projects = user_data.projects
            
            if not projects:
                portfolio.extracted_summary = user_data.profile.summary
                portfolio.extracted_job_title = user_data.profile.job_title
                portfolio.processing_status = ProcessingStatus.COMPLETED
                await self.db.commit()
            else:
                base_title = portfolio.title
                p0 = projects[0]
                
                # Update logic: If multiple projects found, the original record becomes Project 0
                # and new records are created for Project 1..N.
                
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
                portfolio.processing_status = ProcessingStatus.COMPLETED
                portfolio.embedding = embedding0
                
                # Add Job Queries for p0 to main portfolio
                # Note: This appends. Since it's a new extraction, effectively we might want to clear old ones if re-running.
                # But for now assuming clean run.
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
                        processing_status=ProcessingStatus.COMPLETED,
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

                # 5. Trigger Post-Processing (Recommendations & Profile Update) inside JOB context
                # We do this for ALL created portfolios
                
                # Import here to avoid circular dependency at top level if any
                from jobs.services.recruit_service import precompute_recommendations_for_portfolio

                for p in new_portfolios:
                    # 5a. Recommendations
                    try:
                        await precompute_recommendations_for_portfolio(self.db, p.id)
                    except Exception as e:
                        logger.error(f"Post-processing (Recs) failed for {p.id}: {e}")

                    # 5b. Global Profile Update
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
            # Re-fetch to fail status
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            if portfolio:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()
            raise

    async def _update_user_global_profile(self, user_id: int, project_name: str, role: str, tech_stack: str, description: str):
        """
        Helper to trigger global profile update.
        """
        try:
            from common.models import User
            stmt = select(User).where(User.id == user_id)
            res = await self.db.execute(stmt)
            user = res.scalar_one_or_none()
            
            if not user: return

            # Prepare Info
            new_info = f"프로젝트명: {project_name}\n역할: {role}\n기술스택: {tech_stack}\n내용: {description}"
            
            # Call LLM
            updated_profile = await self.llm_refiner.update_global_user_profile(
                current_summary=user.profile_summary or "",
                current_job_title=user.desired_job_title or "",
                new_project_info=new_info
            )
            
            # Update User
            user.profile_summary = updated_profile.get("summary", user.profile_summary)
            user.desired_job_title = updated_profile.get("job_title", user.desired_job_title)
            
            await self.db.commit()
            logger.info(f"Updated global profile for User {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update global profile for user {user_id}: {e}")


