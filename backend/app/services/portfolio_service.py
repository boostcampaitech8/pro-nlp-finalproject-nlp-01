import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import Optional, List

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.models import Portfolio, PortfolioJobQuery, ProcessingStatus
from app.db.database import AsyncSessionLocal
from app.schemas import schemas

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/tmp/uploads")
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create upload directory {UPLOAD_DIR}: {e}")

async def process_portfolio_task(portfolio_id: int, source: str, p_type: str):
    async with AsyncSessionLocal() as db:
        service = PortfolioService(db)
        await service._process_portfolio_logic(portfolio_id, source, p_type)

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
        file_ext = Path(file.filename).suffix
        file_name = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / file_name
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        portfolio = Portfolio(
            title=title, type="file", source_url=str(file_path),
            user_id=user_id, processing_status=ProcessingStatus.PENDING
        )
        self.db.add(portfolio)
        await self.db.commit()
        # Re-fetch with selectinload
        stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
        result = await self.db.execute(stmt)
        portfolio = result.scalar_one()

        background_tasks.add_task(process_portfolio_task, portfolio.id, str(file_path), "file")
        return portfolio

    async def create_portfolio_from_github(self, user_id: int, title: str, github_url: str, background_tasks: BackgroundTasks) -> Portfolio:
        logger.info(f"Creating portfolio for user {user_id}: {title} ({github_url})")
        
        portfolio = Portfolio(
            title=title,
            type="github",
            source_url=github_url,
            user_id=user_id,
            processing_status=ProcessingStatus.PENDING
        )
        self.db.add(portfolio)
        try:
            await self.db.commit()
            # Re-fetch with selectinload
            stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one()
        except Exception as e:
            logger.error(f"Error during portfolio commit: {e}")
            await self.db.rollback()
            raise e

        background_tasks.add_task(process_portfolio_task, portfolio.id, github_url, "github")
        return portfolio

    async def create_portfolio_from_notion(self, user_id: int, title: str, notion_url: str, background_tasks: BackgroundTasks) -> Portfolio:
        portfolio = Portfolio(
            title=title, type="notion", source_url=notion_url,
            user_id=user_id, processing_status=ProcessingStatus.PENDING
        )
        self.db.add(portfolio)
        await self.db.commit()
        # Re-fetch with selectinload
        stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
        result = await self.db.execute(stmt)
        portfolio = result.scalar_one()
        
        background_tasks.add_task(process_portfolio_task, portfolio.id, notion_url, "notion")
        return portfolio

    async def analyze_portfolio_source(self, source: str, p_type: str):
        """Extract and Refine without saving to DB (for preview)."""
        logger.info(f"Analyzing source for preview: {source} ({p_type})")
        try:
            if p_type == "github":
                text = self.github_extractor.extract(source)
            elif p_type == "notion":
                text = self.notion_extractor.extract(source)
            else:
                return {"error": "Unsupported preview type"}

            if not text or "Error" in text[:20]:
                return {"error": text or "Extraction failed"}

            # Call LLM Refiner
            result = self.llm_refiner.extract_user_data_and_queries(text)
            return result
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"error": str(e)}

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
            combined_result = self.llm_refiner.extract_user_data_and_queries(text)
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
                portfolio.project_name = p0.project_name
                portfolio.period = p0.period
                portfolio.role = p0.role
                portfolio.description = p0.description_for_embedding
                portfolio.tech_stack = p0.tech_stack
                portfolio.extracted_summary = user_data.profile.summary
                portfolio.extracted_job_title = user_data.profile.job_title
                portfolio.processing_status = ProcessingStatus.COMPLETED
                
                self.db.add(portfolio)
                new_portfolios = [portfolio]
                
                for proj in projects[1:]:
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
                        tech_stack=proj.tech_stack
                    )
                    self.db.add(new_p)
                    new_portfolios.append(new_p)
                
                for q in combined_result.job_queries.queries:
                    db_q = PortfolioJobQuery(
                        portfolio_id=portfolio.id,
                        type=q.type,
                        query_text=q.query,
                        evidence=q.evidence
                    )
                    self.db.add(db_q)
                
                await self.db.commit()

                # 4. Vector Embedding
                all_docs = []
                from langchain_core.documents import Document
                for p_record in new_portfolios:
                    desc = p_record.description or ""
                    if not desc: continue
                    chunks = self.text_splitter.split_text(desc)
                    for i, chunk in enumerate(chunks):
                        metadata = {
                            "portfolio_id": p_record.id,
                            "type": "project",
                            "project_name": p_record.project_name,
                            "tech_stack": p_record.tech_stack,
                            "chunk_index": i
                        }
                        all_docs.append(Document(page_content=chunk, metadata=metadata))
            
                if all_docs:
                     await self.vector_store.add_documents(all_docs)

        except Exception as e:
            logger.error(f"Processing Failed for Portfolio {portfolio_id}: {e}")
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            if portfolio:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()

# --- Legacy Sync Functions ---
def get_portfolios(db: Session, user_id: int):
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate):
    db_portfolio = Portfolio(**portfolio.model_dump())
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

