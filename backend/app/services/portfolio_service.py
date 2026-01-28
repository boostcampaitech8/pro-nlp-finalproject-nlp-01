import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Portfolio, PortfolioJobQuery, ProcessingStatus

# Standalone function for background task to ensure fresh session
from app.db.database import AsyncSessionLocal

UPLOAD_DIR = Path("/tmp/uploads")
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create upload directory {UPLOAD_DIR}: {e}")

async def process_portfolio_task(portfolio_id: int, source: str, p_type: str):
    async with AsyncSessionLocal() as db:
        service = PortfolioService(db) # specific valid scope
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
        await self.db.refresh(portfolio)

        background_tasks.add_task(process_portfolio_task, portfolio.id, str(file_path), "file")
        return portfolio

    async def create_portfolio_from_github(
        self,
        user_id: int,
        title: str,
        github_url: str,
        background_tasks: BackgroundTasks
    ) -> Portfolio:
        portfolio = Portfolio(
            title=title,
            type="github",
            source_url=github_url,
            user_id=user_id,
            processing_status=ProcessingStatus.PENDING
        )
        self.db.add(portfolio)
        await self.db.commit()
        await self.db.refresh(portfolio)

        background_tasks.add_task(process_portfolio_task, portfolio.id, github_url, "github")
        return portfolio

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

            # Re-fetch main portfolio to ensure we have attached session object or fresh data
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                return

            # Update content on the original/first record
            portfolio.content = text
            await self.db.commit()

            # 2. Refine
            combined_result = self.llm_refiner.extract_user_data_and_queries(text)
            
            # 3. Save Structured Data (Flattened)
            user_data = combined_result.user_data
            
            projects = user_data.projects
            
            if not projects:
                 # Case: No projects found. Just mark completed with summary.
                portfolio.extracted_summary = user_data.profile.summary
                portfolio.extracted_job_title = user_data.profile.job_title
                portfolio.processing_status = ProcessingStatus.COMPLETED
                await self.db.commit()
            else:
                # Case: N Projects found.
                # Method: Update the *first* portfolio record with Project[0]
                #         Create new portfolio records for Project[1..N]
                
                # Common Metadata
                base_title = portfolio.title
                
                # --- Update First Record (Project 0) ---
                p0 = projects[0]
                portfolio.project_name = p0.project_name
                portfolio.period = p0.period
                portfolio.role = p0.role
                portfolio.description = p0.description_for_embedding
                portfolio.tech_stack = p0.tech_stack
                
                portfolio.extracted_summary = user_data.profile.summary
                portfolio.extracted_job_title = user_data.profile.job_title
                portfolio.processing_status = ProcessingStatus.COMPLETED
                
                self.db.add(portfolio) # ensure tracked
                
                # --- Create Records for Project 1..N ---
                new_portfolios = [portfolio] # keep track for vector embedding
                
                for proj in projects[1:]:
                    new_p = Portfolio(
                        title=base_title + f" ({proj.project_name})", # Differentiate title if desired, or keep same
                        type=portfolio.type,
                        source_url=portfolio.source_url,
                        content=text, # Duplicate raw text? Or leave empty to save space? User request implies "3 rows in portfolios", so full copy or reference. Let's keep content for context.
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
                
                # Save Job Queries (Link to the FIRST portfolio or ALL? 
                # Usually queries are global for the user. Let's link to the first one for now to avoid duplication of queries.)
                # OR, if queries are specific... Refiner generates global queries.
                # Let's attach queries to the first record.
                for q in combined_result.job_queries.queries:
                    db_q = PortfolioJobQuery(
                        portfolio_id=portfolio.id,
                        type=q.type,
                        query_text=q.query,
                        evidence=q.evidence
                    )
                    self.db.add(db_q)
                
                await self.db.commit()

                # 4. Vector Embedding (For ALL created portfolios)
                all_docs = []
                
                for p_record in new_portfolios:
                    # Refresh to get ID if new
                    # await self.db.refresh(p_record) # Might be needed if IDs are not populated yet
                    
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
                        from langchain_core.documents import Document
                        all_docs.append(Document(page_content=chunk, metadata=metadata))
            
                if all_docs:
                     await self.vector_store.add_documents(all_docs)

        except Exception as e:
            print(f"Processing Failed for Portfolio {portfolio_id}: {e}")
            # Re-fetch to mark failed
            stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            if portfolio:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()

    async def get_portfolio(self, portfolio_id: int):
        stmt = select(Portfolio).where(Portfolio.id == portfolio_id)

# ---------------------------------------------------------
# Legacy / Sync CRUD Functions for compatibility with existing endpoints
# ---------------------------------------------------------
from sqlalchemy.orm import Session
from app.schemas import schemas

def get_portfolios(db: Session, user_id: int):
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate):
    db_portfolio = Portfolio(**portfolio.dict())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def get_portfolio(db: Session, portfolio_id: int, user_id: int):
    return db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()

def update_portfolio(db: Session, portfolio_id: int, user_id: int, portfolio_data: dict):
    db_portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not db_portfolio:
        return None
    for key, value in portfolio_data.items():
        setattr(db_portfolio, key, value)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def delete_portfolio(db: Session, portfolio_id: int, user_id: int):
    db_portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not db_portfolio:
        return False
    db.delete(db_portfolio)
    db.commit()
    return True

def mock_analyze_portfolio(source: str, type: str):
    return [{"analysis": "Mock analysis result for " + source}]

