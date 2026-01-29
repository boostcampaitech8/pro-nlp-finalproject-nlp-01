import os
import shutil
import uuid
import logging
from langchain_core.documents import Document
from pathlib import Path
from typing import Optional, List

from fastapi import UploadFile, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.models import Portfolio, PortfolioJobQuery, ProcessingStatus
from app.db.database import AsyncSessionLocal
from app.schemas import schemas
from app.services import recruit_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/tmp/uploads")
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create upload directory {UPLOAD_DIR}: {e}")

async def process_portfolio_task(portfolio_id: int, source: str, p_type: str):
    try:
        async with AsyncSessionLocal() as db:
            service = PortfolioService(db)
            await service._process_portfolio_logic(portfolio_id, source, p_type)
    finally:
        if p_type == "file" and source:
            try:
                path = Path(source)
                if path.exists() and "/tmp/uploads" in str(path):
                    os.remove(path)
                    logger.info(f"Cleaned up temporary file: {source}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {source}: {e}")

class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._file_extractor = None
        self._notion_extractor = None
        self._github_extractor = None
        self._llm_refiner = None
        self._vector_store = None
        self._text_splitter = None

    @property
    def file_extractor(self):
        if not self._file_extractor:
            from app.core.portfolio.extractors.file_extractor import FileExtractor
            self._file_extractor = FileExtractor()
        return self._file_extractor

    @property
    def notion_extractor(self):
        if not self._notion_extractor:
            from app.core.portfolio.extractors.notion_extractor import NotionExtractor
            self._notion_extractor = NotionExtractor()
        return self._notion_extractor

    @property
    def github_extractor(self):
        if not self._github_extractor:
            from app.core.portfolio.extractors.github_extractor import GitHubExtractor
            self._github_extractor = GitHubExtractor()
        return self._github_extractor

    @property
    def llm_refiner(self):
        if not self._llm_refiner:
            from app.core.portfolio.processors.llm_refiner import LLMRefiner
            self._llm_refiner = LLMRefiner()
        return self._llm_refiner

    @property
    def vector_store(self):
        if not self._vector_store:
            from app.core.portfolio.storage.supabase_vector_store import SupabaseVectorStore
            self._vector_store = SupabaseVectorStore()
        return self._vector_store

    @property
    def text_splitter(self):
        if not self._text_splitter:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", ".", " "]
            )
        return self._text_splitter

    async def create_portfolio_from_file(self, user_id: int, title: str, file: UploadFile, background_tasks: BackgroundTasks):
        """
        Upload a file, extract text, analyze with AI, and save all projects.
        Returns the first portfolio created (for backward compatibility).
        """
        logger.info(f"Creating portfolio from file for user {user_id}: {title}")
        
        # 1. Save file
        file_ext = Path(file.filename).suffix
        file_name = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / file_name
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # 2. Extract text
            text = self.file_extractor.extract(str(file_path))
            
            if not text or text.startswith("[Error]"):
                raise HTTPException(status_code=500, detail=f"Text extraction failed: {text}")
            
            # 3. AI Analysis
            ai_result = await self.llm_refiner.extract_user_data_and_queries(text)
            
            if not ai_result.user_data.projects:
                raise HTTPException(status_code=500, detail="No projects extracted from portfolio")
            
            # 4. Save all projects as separate Portfolio records
            portfolios = await self.save_verified_portfolios_from_ai(
                user_id=user_id,
                ai_result=ai_result,
                original_title=title,
                p_type="file",
                source_url=str(file_path)
            )
            
            # 5. Trigger background recommendation update
            background_tasks.add_task(recruit_service.run_bg_recalc_for_user, user_id)
            
            # Return first portfolio for backward compatibility
            return portfolios[0] if portfolios else None
            
        except Exception as e:
            logger.error(f"Portfolio creation failed: {e}")
            # Clean up file on error
            if file_path.exists():
                file_path.unlink()
            raise

    async def create_portfolio_from_github(self, user_id: int, title: str, github_url: str, background_tasks: BackgroundTasks) -> Portfolio:
        """
        Import from GitHub, extract text, analyze with AI, and save all projects.
        Returns the first portfolio created (for backward compatibility).
        """
        logger.info(f"Creating portfolio from GitHub for user {user_id}: {title} ({github_url})")
        
        try:
            # 1. Extract text from GitHub
            text = self.github_extractor.extract(github_url)
            
            if not text or text.startswith("[Error]"):
                raise HTTPException(status_code=500, detail=f"GitHub extraction failed: {text}")
            
            # 2. AI Analysis
            ai_result = await self.llm_refiner.extract_user_data_and_queries(text)
            
            if not ai_result.user_data.projects:
                raise HTTPException(status_code=500, detail="No projects extracted from GitHub")
            
            # 3. Save all projects as separate Portfolio records
            portfolios = await self.save_verified_portfolios_from_ai(
                user_id=user_id,
                ai_result=ai_result,
                original_title=title,
                p_type="github",
                source_url=github_url
            )
            
            # 4. Trigger background recommendation update
            background_tasks.add_task(recruit_service.run_bg_recalc_for_user, user_id)
            
            # Return first portfolio for backward compatibility
            return portfolios[0] if portfolios else None
            
        except Exception as e:
            logger.error(f"GitHub portfolio creation failed: {e}")
            raise

    async def create_portfolio_from_notion(self, user_id: int, title: str, notion_url: str, background_tasks: BackgroundTasks) -> Portfolio:
        """
        Import from Notion, extract text, analyze with AI, and save all projects.
        Returns the first portfolio created (for backward compatibility).
        """
        logger.info(f"Creating portfolio from Notion for user {user_id}: {title} ({notion_url})")
        
        try:
            # 1. Extract text from Notion
            text = self.notion_extractor.extract(notion_url)
            
            if not text or text.startswith("[Error]"):
                raise HTTPException(status_code=500, detail=f"Notion extraction failed: {text}")
            
            # 2. AI Analysis
            ai_result = await self.llm_refiner.extract_user_data_and_queries(text)
            
            if not ai_result.user_data.projects:
                raise HTTPException(status_code=500, detail="No projects extracted from Notion")
            
            # 3. Save all projects as separate Portfolio records
            portfolios = await self.save_verified_portfolios_from_ai(
                user_id=user_id,
                ai_result=ai_result,
                original_title=title,
                p_type="notion",
                source_url=notion_url
            )
            
            # 4. Trigger background recommendation update
            background_tasks.add_task(recruit_service.run_bg_recalc_for_user, user_id)
            
            # Return first portfolio for backward compatibility
            return portfolios[0] if portfolios else None
            
        except Exception as e:
            logger.error(f"Notion portfolio creation failed: {e}")
            raise

    async def save_verified_portfolio(self, user_id: int, req: schemas.PortfolioCreateRequest):
        """Save a portfolio that has been reviewed and verified by the user.
        
        NOTE: This now creates ONE Portfolio record per project in the AI extraction.
        Each project gets its own A/B/C job queries.
        """
        logger.info(f"Saving verified portfolio for user {user_id}: {req.project_name}")
        
        job_queries_data = req.job_queries or []
        logger.info(f"Received {len(job_queries_data)} job queries from request.")
        
        data = req.model_dump(exclude={"job_queries"})
        
        # Explicitly create job query models
        db_queries = []
        for i, jq in enumerate(job_queries_data):
            logger.debug(f"JQ[{i}]: type={jq.type}, text={jq.query_text[:30]}...")
            
            q_emb = None
            if jq.query_text:
                try:
                    q_emb = await self.vector_store.get_embedding(jq.query_text)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for job query '{jq.query_text}': {e}")

            db_queries.append(
                PortfolioJobQuery(
                    type=jq.type,
                    query_text=jq.query_text,
                    evidence=jq.evidence if hasattr(jq, 'evidence') else [],
                    embedding=q_emb
                )
            )

        # 1. Generate Embedding for 1:1 storage
        desc = req.description or ""
        embedding = None
        if desc:
            try:
                embedding = await self.vector_store.get_embedding(desc)
            except Exception as e:
                logger.error(f"Failed to generate embedding during manual save: {e}")

        portfolio = Portfolio(
            **data,
            user_id=user_id,
            processing_status=ProcessingStatus.COMPLETED,
            job_queries=db_queries,
            embedding=embedding
        )
        
        self.db.add(portfolio)
        try:
            await self.db.commit()
            logger.info(f"Successfully committed portfolio {portfolio.id} with {len(portfolio.job_queries)} queries")
        except Exception as e:
            logger.error(f"Failed to commit portfolio: {e}")
            await self.db.rollback()
            raise
        
        # Re-fetch with selectinload to avoid detaching issues during JSON serialization
        stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
        result = await self.db.execute(stmt)
        portfolio = result.scalar_one()

        # 2. Add to Vector Store for RAG - REMOVED (We use direct DB embeddings now)
        # The embedding is already stored in the Portfolio.embedding column.

        # 3. Trigger Global Profile Update (Incremental Learning)
        await self._update_user_global_profile(
            user_id=user_id,
            project_name=req.project_name,
            role=req.role or "",
            tech_stack=", ".join(req.tech_stack) if req.tech_stack else "",
            description=req.description or ""
        )

        return portfolio
    
    async def save_verified_portfolios_from_ai(self, user_id: int, ai_result, original_title: str, p_type: str, source_url: str = None):
        """Save multiple Portfolio records from AI extraction - one per project.
        
        Args:
            user_id: User ID
            ai_result: CombinedResult from LLM with user_data.projects list
            original_title: Original portfolio title/filename
            p_type: Portfolio type (file, github, notion, etc.)
            source_url: Optional source URL
            
        Returns:
            List of created Portfolio records
        """
        logger.info(f"Saving {len(ai_result.user_data.projects)} projects as separate portfolios for user {user_id}")
        
        created_portfolios = []
        
        for idx, project in enumerate(ai_result.user_data.projects):
            # Create title combining original title and project name
            portfolio_title = f"{original_title} - {project.project_name}"
            
            # Convert project's job_queries to PortfolioJobQuery models
            db_queries = []
            for jq in project.job_queries:
                db_queries.append(
                    PortfolioJobQuery(
                        type=jq.type,
                        query_text=jq.query,
                        evidence=jq.evidence
                    )
                )
            
            # Generate embedding for 1:1 storage
            desc = project.description_for_embedding or ""
            embedding = None
            if desc:
                try:
                    embedding = await self.vector_store.get_embedding(desc)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for project {project.project_name}: {e}")

            # Create Portfolio record
            portfolio = Portfolio(
                title=portfolio_title,
                type=p_type,
                source_url=source_url,
                content=None,  # Raw text not stored per-project
                user_id=user_id,
                processing_status=ProcessingStatus.COMPLETED,
                extracted_summary=ai_result.user_data.profile.summary,
                extracted_job_title=ai_result.user_data.profile.job_title,
                project_name=project.project_name,
                period=project.period,
                role=project.role,
                description=project.description_for_embedding,
                tech_stack=project.tech_stack,
                job_queries=db_queries,
                embedding=embedding
            )
            
            self.db.add(portfolio)
            created_portfolios.append(portfolio)
        
        # Commit all at once
        try:
            await self.db.commit()
            logger.info(f"Successfully committed {len(created_portfolios)} portfolio records")
        except Exception as e:
            logger.error(f"Failed to commit portfolios: {e}")
            await self.db.rollback()
            raise
        
        # Re-fetch with relationships and add to vector store
        portfolio_ids = [p.id for p in created_portfolios]
        stmt = select(Portfolio).where(Portfolio.id.in_(portfolio_ids)).options(selectinload(Portfolio.job_queries))
        result = await self.db.execute(stmt)
        portfolios = result.scalars().all()
        
        # 4. Trigger Global Profile Update (Incremental Learning)
        # We can update profile for each project or aggregate. Updating per project ensures detail.
        for project in ai_result.user_data.projects:
             await self._update_user_global_profile(
                user_id=user_id,
                project_name=project.project_name,
                role=project.role or "",
                tech_stack=", ".join(project.tech_stack) if project.tech_stack else "",
                description=project.description_for_embedding or ""
            )

        return portfolios
        
        return portfolios

    async def analyze_portfolio_source(self, source: str, p_type: str):
        """Extract and Refine without saving to DB (for preview)."""
        logger.info(f"Analyzing source for preview: {source} ({p_type})")
        try:
            if p_type == "github":
                text = self.github_extractor.extract(source)
            elif p_type == "notion":
                text = self.notion_extractor.extract(source)
            else:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Unsupported preview type")

            if not text or "Error" in text[:20]:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail=text or "Extraction failed")

            # Call LLM Refiner
            result = await self.llm_refiner.extract_user_data_and_queries(text)
            
            # Combine with raw text for preview
            return {
                "user_data": result.user_data.model_dump(),
                "raw_text": text
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    async def analyze_portfolio_file(self, file: UploadFile):
        """Extract and Refine an uploaded file without saving to DB (for preview)."""
        logger.info(f"Analyzing uploaded file for preview: {file.filename}")
        
        # Save temp file
        temp_id = uuid.uuid4()
        temp_path = UPLOAD_DIR / f"temp_{temp_id}_{file.filename}"
        
        try:
            with temp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            text = self.file_extractor.extract(str(temp_path))
            
            if not text or text.startswith("[Error]") or "Error" in text[:20]:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail=text or "Extraction failed")

            # Call LLM Refiner
            result = await self.llm_refiner.extract_user_data_and_queries(text)
            
            # Combine with raw text for preview
            return {
                "user_data": result.user_data.model_dump(),
                "raw_text": text
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File analysis failed: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if temp_path.exists():
                temp_path.unlink()

    async def _process_portfolio_logic(self, portfolio_id: int, source: str, p_type: str):
        try:
            # 1. Extract
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

            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            if not portfolio: return

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
                # Generate embedding for 1:1 storage (p0)
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
                
                self.db.add(portfolio)
                new_portfolios = [portfolio]
                
                for proj in projects[1:]:
                    # Generate embedding for 1:1 storage
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
                    self.db.add(new_p)
                    new_portfolios.append(new_p)
                
                # 4. Save Job Queries (using first project's queries for the main portfolio record logic if needed, 
                # OR actually the loop above already attached queries to NEW portfolios. 
                # This block seems to be trying to attach queries to the ORIGINAL portfolio (portfolio_id).
                # Since we decided (line 517) that 'portfolio' becomes project 0, we should add queries from project 0.
                
                # However, the loop above (lines 530-557) created new portfolios for projects[1:]. 
                # Ideally, we should add queries to 'portfolio' (which is p0) here too.
                
                # Check line 365 in save_verified_portfolios: it adds queries to ALL portfolios.
                # Here, 'portfolio' is p0. So we should add p0's queries.
                
                # Clear existing queries first if any?
                # portfolio is existing record.
                
                for jq in p0.job_queries:
                    # Pre-embed the job query for faster matching
                    q_emb = None
                    # Use existing embedding if available? No, QueryItem has no embedding field.
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
                
                await self.db.commit()
                logger.info(f"Successfully processed portfolio {portfolio.id} with {len(portfolio.job_queries)} queries (pre-embedded)")
                
                # 5. Pre-compute Recommendations
                from app.services.recruit_service import precompute_recommendations_for_portfolio
                await precompute_recommendations_for_portfolio(self.db, portfolio_id)

                # 6. Trigger Global Profile Update (Incremental Learning)
                # First Project (p0)
                await self._update_user_global_profile(
                    user_id=portfolio.user_id,
                    project_name=p0.project_name,
                    role=p0.role or "",
                    tech_stack=", ".join(p0.tech_stack) if p0.tech_stack else "",
                    description=p0.description_for_embedding or ""
                )
                
                # Subsequent Projects
                for proj in projects[1:]:
                     await self._update_user_global_profile(
                        user_id=portfolio.user_id,
                        project_name=proj.project_name,
                        role=proj.role or "",
                        tech_stack=", ".join(proj.tech_stack) if proj.tech_stack else "",
                        description=proj.description_for_embedding or ""
                    )

        except Exception as e:
            logger.error(f"Processing Failed for Portfolio {portfolio_id}: {e}")
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            if portfolio:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()

    async def _update_user_global_profile(self, user_id: int, project_name: str, role: str, tech_stack: str, description: str):
        """
        Helper to trigger global profile update.
        """
        try:
            from app.models.models import User
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

# --- Legacy Sync Functions ---
def get_portfolios(db: Session, user_id: int):
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate):
    db_portfolio = Portfolio(**portfolio.model_dump())
    # If explicitly saved from UI, we mark it COMPLETED since it's already "reviewed"
    db_portfolio.processing_status = ProcessingStatus.COMPLETED
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def get_portfolio(db: Session, portfolio_id: int, user_id: int):
    return db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()

def update_portfolio(db: Session, portfolio_id: int, user_id: int, portfolio_data: dict):
    db_portfolio = get_portfolio(db, portfolio_id, user_id)
    if not db_portfolio: return None
    for key, value in portfolio_data.items():
        setattr(db_portfolio, key, value)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def delete_portfolio(db: Session, portfolio_id: int, user_id: int):
    db_portfolio = get_portfolio(db, portfolio_id, user_id)
    if not db_portfolio: return False
    db.delete(db_portfolio)
    db.commit()
    return True

def mock_analyze_portfolio(source: str, type: str):
    return [{"analysis": "Mock result for " + source}]

