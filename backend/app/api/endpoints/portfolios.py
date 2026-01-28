from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.database import get_db, get_async_db
from app.schemas import schemas
from app.services import portfolio_service
from app.services.portfolio_service import PortfolioService
from app.api import deps
from app.models import models

router = APIRouter()

@router.get("", response_model=schemas.PortfolioListResponse)
async def list_portfolios(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    items = portfolio_service.get_portfolios(db, user_id=current_user.id)
    return {"items": items}

@router.post("", response_model=schemas.Portfolio, status_code=201)
async def create_portfolio(
    portfolio: schemas.PortfolioCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = PortfolioService(db)
    return await service.save_verified_portfolio(current_user.id, portfolio)

@router.post("/upload", response_model=schemas.Portfolio, status_code=201)
async def upload_portfolio(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Upload a portfolio file (PDF/TXT/MD), save it, and trigger background extraction/refinement.
    """
    service = PortfolioService(db)
    return await service.create_portfolio_from_file(current_user.id, title, file, background_tasks)

@router.post("/notion", response_model=schemas.Portfolio, status_code=201)
async def import_notion_portfolio(
    background_tasks: BackgroundTasks,
    payload: schemas.PortfolioCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Import portfolio from a Notion URL.
    """
    service = PortfolioService(db)
    return await service.create_portfolio_from_notion(current_user.id, payload.title, payload.source_url, background_tasks)

@router.post("/github", response_model=schemas.Portfolio, status_code=201)
async def import_github_portfolio(
    background_tasks: BackgroundTasks,
    payload: schemas.PortfolioCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Import portfolio from a GitHub Repository or User Profile URL/ID.
    """
    service = PortfolioService(db)
    return await service.create_portfolio_from_github(current_user.id, payload.title, payload.source_url, background_tasks)

@router.get("/{portfolio_id}", response_model=schemas.Portfolio)
async def get_portfolio(
    portfolio_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    portfolio = portfolio_service.get_portfolio(db, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.patch("/{portfolio_id}", response_model=schemas.Portfolio)
async def update_portfolio(
    portfolio_id: int,
    portfolio: schemas.PortfolioUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    updated_portfolio = portfolio_service.update_portfolio(
        db, portfolio_id, current_user.id, portfolio.model_dump(exclude_unset=True)
    )
    if not updated_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")
    return updated_portfolio

@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    success = portfolio_service.delete_portfolio(db, portfolio_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")
    return {"success": True, "message": "Portfolio deleted"}

@router.post("/analyze")
async def analyze_portfolio(
    req: schemas.PortfolioAnalyzeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Real AI analysis of a portfolio source for preview."""
    service = PortfolioService(db)
    return await service.analyze_portfolio_source(req.source, req.type)
