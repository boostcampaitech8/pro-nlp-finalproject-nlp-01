import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import Optional, List

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from common.models import Portfolio, ProcessingStatus
from common.database import AsyncSessionLocal
from common import schemas
from app.services.job_service import job_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/tmp/uploads")
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create upload directory {UPLOAD_DIR}: {e}")

class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_portfolio_from_file(self, user_id: int, title: str, file: UploadFile):
        """
        Upload a file and trigger a background extraction job.
        """
        logger.info(f"Creating portfolio from file for user {user_id}: {title}")
        
        file_ext = Path(file.filename).suffix
        file_name = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / file_name
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # 1. Save placeholder Portfolio record
            portfolio = Portfolio(
                project_name=title, # Placeholder
                type="file",
                source_url=str(file_path),
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # 2. Trigger background job
            job_service.trigger_job(task="portfolio_extraction", target_id=portfolio.id)
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Portfolio creation failed: {e}")
            if file_path.exists():
                file_path.unlink()
            raise

    async def create_portfolio_from_github(self, user_id: int, title: str, github_url: str) -> Portfolio:
        """
        Trigger a GitHub extraction job.
        """
        logger.info(f"Creating portfolio from GitHub for user {user_id}: {title} ({github_url})")
        
        try:
            portfolio = Portfolio(
                project_name=title,
                type="github",
                source_url=github_url,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            job_service.trigger_job(task="portfolio_extraction", target_id=portfolio.id)
            return portfolio
        except Exception as e:
            logger.error(f"GitHub portfolio creation failed: {e}")
            raise

    async def create_portfolio_from_notion(self, user_id: int, title: str, notion_url: str) -> Portfolio:
        """
        Trigger a Notion extraction job.
        """
        logger.info(f"Creating portfolio from Notion for user {user_id}: {title} ({notion_url})")
        
        try:
            portfolio = Portfolio(
                project_name=title,
                type="notion",
                source_url=notion_url,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            job_service.trigger_job(task="portfolio_extraction", target_id=portfolio.id)
            return portfolio
        except Exception as e:
            logger.error(f"Notion portfolio creation failed: {e}")
            raise

    async def save_verified_portfolio(self, user_id: int, req: schemas.PortfolioCreateRequest):
        """
        Save a portfolio that has been reviewed by the user.
        Note: The heavy embedding parts are now triggered as post-save updates if needed,
        but typically the AI already generated them.
        """
        logger.info(f"Saving verified portfolio for user {user_id}: {req.project_name}")
        
        # We can still save metadata directly
        data = req.model_dump(exclude={"job_queries"})
        portfolio = Portfolio(
            **data,
            user_id=user_id,
            processing_status=ProcessingStatus.COMPLETED
        )
        # Note: Embedding and job_queries should ideally come from the request if already generated
        # or we trigger a light job to update them.
        
        self.db.add(portfolio)
        await self.db.commit()
        await self.db.refresh(portfolio)
        
        # Trigger any post-save heavy updates (e.g. global profile update)
        job_service.trigger_job(task="recruit_update", target_id=user_id)
        
        return portfolio

    async def get_portfolios(self, user_id: int):
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_portfolio(self, portfolio_id: int, user_id: int):
        stmt = (
            select(Portfolio)
            .options(selectinload(Portfolio.job_queries))
            .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_portfolio(self, portfolio_id: int, user_id: int, portfolio_data: dict):
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        
        for key, value in portfolio_data.items():
            setattr(portfolio, key, value)
        
        await self.db.commit()
        await self.db.refresh(portfolio)
        return portfolio

    async def delete_portfolio(self, portfolio_id: int, user_id: int):
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False
        
        await self.db.delete(portfolio)
        await self.db.commit()
        return True

    async def analyze_portfolio_source(self, user_id: int, source: str, p_type: str):
        """
        Asynchronous analysis of a portfolio source for preview.
        Offloads the extraction to a Cloud Run Job.
        """
        logger.info(f"Analyzing portfolio source asynchronously: {source} ({p_type})")
        
        try:
            # 1. Create a placeholder record for analysis
            portfolio = Portfolio(
                project_name=f"Analysis: {source[:20]}",
                type=p_type,
                source_url=source,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # 2. Trigger analysis job
            success = job_service.trigger_job(task="portfolio_analysis", target_id=portfolio.id)
            
            if not success:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()
                return {"error": "Failed to trigger analysis job (Infrastructure error)", "success": False}
                
            return {"portfolio_id": portfolio.id, "status": "PENDING", "success": True}
        except Exception as e:
            logger.error(f"Async analysis trigger failed: {e}")
            return {"error": str(e), "success": False}

    async def analyze_portfolio_file(self, user_id: int, file: UploadFile):
        """
        Asynchronous analysis of an uploaded file.
        Offloads extraction to a Cloud Run Job.
        """
        logger.info(f"Analyzing portfolio file asynchronously: {file.filename}")
        
        file_ext = Path(file.filename).suffix
        file_name = f"analyze_{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / file_name
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 1. Create placeholder
            portfolio = Portfolio(
                project_name=f"Analysis: {file.filename}",
                type="file",
                source_url=str(file_path),
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # 2. Trigger job
            success = job_service.trigger_job(task="portfolio_analysis", target_id=portfolio.id)
            
            if not success:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()
                return {"error": "Failed to trigger analysis job (Infrastructure error)", "success": False}
                
            return {"portfolio_id": portfolio.id, "status": "PENDING", "success": True}
        except Exception as e:
             logger.error(f"Async file analysis trigger failed: {e}")
             if file_path.exists():
                 file_path.unlink()
             return {"error": str(e), "success": False}



