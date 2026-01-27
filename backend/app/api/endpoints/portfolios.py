from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas import schemas
from app.schemas import schemas
from app.services import portfolio_service
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

@router.post("/", response_model=schemas.Portfolio, status_code=201)
async def create_portfolio(
    portfolio: schemas.PortfolioCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    portfolio_data = portfolio.model_dump()
    internal_portfolio = schemas.PortfolioCreate(**portfolio_data, user_id=current_user.id)
    return portfolio_service.create_portfolio(db, internal_portfolio)

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
    portfolio: schemas.PortfolioCreateRequest,
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

@router.post("/analyze", response_model=List[dict])
async def analyze_portfolio(
    req: schemas.PortfolioAnalyzeRequest,
    current_user: models.User = Depends(deps.get_current_user)
):
    """Mocks AI analysis of a portfolio source."""
    return portfolio_service.mock_analyze_portfolio(req.source, req.type)
