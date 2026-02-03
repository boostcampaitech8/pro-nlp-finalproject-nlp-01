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
from common.gcs_utils import gcs_utils

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
        
        # Save locally temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # 2. Upload to GCS
            remote_path = f"portfolios/{user_id}/{file_name}"
            gs_uri = gcs_utils.upload_file(str(file_path), remote_path)
            
            # 3. Save placeholder Portfolio record with GCS URI
            portfolio = Portfolio(
                project_name=title, # Placeholder
                type="file",
                source_url=gs_uri,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # 4. Trigger background job
            job_service.trigger_portfolio_extraction(portfolio_id=portfolio.id)
            
            # Clean up local file after upload
            if file_path.exists():
                file_path.unlink()
                
            return portfolio
            
        except Exception as e:
            logger.error(f"Portfolio creation failed: {e}")
            await self.db.rollback()
            if file_path.exists():
                file_path.unlink()
            raise

    async def create_portfolio_from_github(self, user_id: int, project_name: str, github_url: str) -> Portfolio:
        """
        Trigger a GitHub extraction job.
        """
        logger.info(f"Creating portfolio from GitHub for user {user_id}: {project_name} ({github_url})")
        
        try:
            portfolio = Portfolio(
                project_name=project_name,
                type="github",
                source_url=github_url,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            
            # Explicitly load relationships to prevent MissingGreenlet error
            stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one()
            
            job_service.trigger_portfolio_extraction(portfolio_id=portfolio.id)
            return portfolio
        except Exception as e:
            logger.error(f"GitHub portfolio creation failed: {e}")
            await self.db.rollback()
            raise

    async def create_portfolio_from_notion(self, user_id: int, project_name: str, notion_url: str) -> Portfolio:
        """
        Trigger a Notion extraction job.
        """
        logger.info(f"Creating portfolio from Notion for user {user_id}: {project_name} ({notion_url})")
        
        try:
            portfolio = Portfolio(
                project_name=project_name,
                type="notion",
                source_url=notion_url,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            
            # Explicitly load relationships to prevent MissingGreenlet error
            stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one()
            
            job_service.trigger_portfolio_extraction(portfolio_id=portfolio.id)
            return portfolio
        except Exception as e:
            logger.error(f"Notion portfolio creation failed: {e}")
            await self.db.rollback()
            raise

    async def create_portfolio_from_blog(self, user_id: int, project_name: str, blog_url: str) -> Portfolio:
        """
        Trigger a Blog extraction job.
        """
        logger.info(f"Creating portfolio from Blog for user {user_id}: {project_name} ({blog_url})")
        
        try:
            portfolio = Portfolio(
                project_name=project_name,
                type="blog",
                source_url=blog_url,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            
            # Explicitly load relationships to prevent MissingGreenlet error
            stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(selectinload(Portfolio.job_queries))
            result = await self.db.execute(stmt)
            portfolio = result.scalar_one()
            
            job_service.trigger_portfolio_extraction(portfolio_id=portfolio.id)
            return portfolio
        except Exception as e:
            logger.error(f"Blog portfolio creation failed: {e}")
            await self.db.rollback()
            raise

    async def save_verified_portfolio(self, user_id: int, req: schemas.PortfolioCreateRequest):
        """
        Save a portfolio that has been reviewed by the user.
        """
        logger.info(f"Saving verified portfolio for user {user_id}: {req.project_name}")
        
        data = req.model_dump(exclude={"job_queries"})
        portfolio = Portfolio(
            **data,
            user_id=user_id,
            processing_status=ProcessingStatus.COMPLETED
        )
        
        self.db.add(portfolio)
        await self.db.commit()
        
        # Explicitly load relationships to prevent MissingGreenlet error
        stmt = select(Portfolio).where(Portfolio.id == portfolio.id).options(
            selectinload(Portfolio.job_queries)
        )
        result = await self.db.execute(stmt)
        portfolio = result.scalar_one()
        
        job_service.trigger_recommendation_update(user_id=user_id)
        
        return portfolio

    async def get_portfolios(self, user_id: int):
        stmt = select(Portfolio).where(Portfolio.user_id == user_id).options(
            selectinload(Portfolio.job_queries)
        )
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

    async def update_portfolio(self, portfolio_id: int, user_id: int, portfolio_data: schemas.PortfolioUpdateRequest):
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        
        data = portfolio_data.model_dump(exclude_unset=True)
        for key, value in data.items():
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
            success = job_service.trigger_portfolio_analysis(portfolio_id=portfolio.id)
            
            if not success:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()
                return {"error": "Failed to trigger analysis job (Infrastructure error)", "success": False}
                
            return {"portfolio_id": portfolio.id, "status": "PENDING", "success": True}
        except Exception as e:
            logger.error(f"Async analysis trigger failed: {e}")
            await self.db.rollback()
            return {"error": str(e), "success": False}

    async def analyze_portfolio_file(self, user_id: int, file: UploadFile):
        """
        Asynchronous analysis of an uploaded file.
        """
        logger.info(f"Analyzing portfolio file asynchronously: {file.filename}")
        
        file_ext = Path(file.filename).suffix
        file_name = f"analyze_{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / file_name
        
        # Save locally temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # 2. Upload to GCS
            remote_path = f"analysis/{user_id}/{file_name}"
            gs_uri = gcs_utils.upload_file(str(file_path), remote_path)
            
            # 3. Create placeholder with GCS URI
            portfolio = Portfolio(
                project_name=f"Analysis: {file.filename}",
                type="file",
                source_url=gs_uri,
                user_id=user_id,
                processing_status=ProcessingStatus.PENDING
            )
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
            
            # 4. Trigger job
            success = job_service.trigger_portfolio_analysis(portfolio_id=portfolio.id)
            
            if not success:
                portfolio.processing_status = ProcessingStatus.FAILED
                await self.db.commit()
                return {"error": "Failed to trigger analysis job (Infrastructure error)", "success": False}
                
            # Clean up local file
            if file_path.exists():
                file_path.unlink()
                
            return {"portfolio_id": portfolio.id, "status": "PENDING", "success": True}
            
        except Exception as e:
             logger.error(f"Async file analysis trigger failed: {e}")
             await self.db.rollback()
             if file_path.exists():
                 file_path.unlink()
             return {"error": str(e), "success": False}
