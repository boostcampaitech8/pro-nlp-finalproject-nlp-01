from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas

def get_portfolios(db: Session, user_id: int):
    return db.query(models.Portfolio).filter(models.Portfolio.user_id == user_id).all()

def get_portfolio(db: Session, portfolio_id: int, user_id: int):
    return db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id, models.Portfolio.user_id == user_id).first()

def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate):
    db_portfolio = models.Portfolio(**portfolio.model_dump())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def update_portfolio(db: Session, portfolio_id: int, user_id: int, portfolio_data: dict):
    db_portfolio = get_portfolio(db, portfolio_id, user_id)
    if not db_portfolio:
        return None
    for key, value in portfolio_data.items():
        setattr(db_portfolio, key, value)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def delete_portfolio(db: Session, portfolio_id: int, user_id: int):
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id, models.Portfolio.user_id == user_id).first()
    if not db_portfolio:
        return False
    db.delete(db_portfolio)
    db.commit()
    return True

def mock_analyze_portfolio(source: str, portfolio_type: str):
    # Mock data for AI analysis
    return [
        {
            "id": 101,
            "title": f"Analyzed Project from {source}",
            "type": portfolio_type,
            "description": "AI-generated description of your project.",
            "content": "Detailed technical challenges and solutions extracted by AI.",
            "createdAt": "2026-01-24"
        }
    ]
