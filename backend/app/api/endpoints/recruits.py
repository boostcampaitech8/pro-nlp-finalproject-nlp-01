from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
from app.db.database import get_async_db
from app.schemas import schemas
from app.services import recruit_service
from app.api import deps
from app.models import models

router = APIRouter()

@router.get("", response_model=schemas.RecruitmentListResponse)
async def list_recruits(
    background_tasks: BackgroundTasks,
    page: int = 1, 
    limit: int = 10, 
    category: Optional[str] = None, 
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[models.User] = Depends(deps.get_current_user_optional)
):
    skip = (page - 1) * limit
    items, total = await recruit_service.get_recruitments(
        db, skip=skip, limit=limit, category=category, keyword=keyword, location=location
    )
    
    # Pre-compute recommendations in background if user is logged in
    if current_user:
        background_tasks.add_task(recruit_service.run_bg_recalc_for_user, current_user.id)
        
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total > 0 else 0
        }
    }

@router.get("/recommend", response_model=Dict)
async def get_recommendations(
    portfolio_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Get AI-powered recruitment recommendations based on user portfolio.
    """
    return await recruit_service.get_ai_recommendations(db, current_user.id, portfolio_id)

@router.get("/{recruit_id}", response_model=schemas.Recruitment)
async def get_recruit(recruit_id: int, db: AsyncSession = Depends(get_async_db)):
    db_recruit = await recruit_service.get_recruitment(db, recruit_id)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return db_recruit

@router.post("", response_model=schemas.Recruitment, status_code=201)
async def create_recruit(
    recruit: schemas.RecruitmentCreate, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Admin endpoint to create a new recruitment posting."""
    return await recruit_service.create_recruitment(db, recruit)

@router.post("/index", status_code=201)
async def index_recruitments(
    payload: List[Dict] = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Bulk index recruitment data into vector store.
    """
    from app.core.recruit.indexer import RecruitIndexer
    indexer = RecruitIndexer()
    count = await indexer.add_recruitments(db, payload)
    return {"message": f"Successfully indexed {count} recruitments"}

@router.put("/{recruit_id}", response_model=schemas.Recruitment)
async def update_recruit(
    recruit_id: int, 
    recruit: schemas.RecruitmentCreate, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Admin endpoint to update a recruitment posting."""
    db_recruit = await recruit_service.update_recruitment(db, recruit_id, recruit)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return db_recruit

@router.delete("/{recruit_id}")
async def delete_recruit(
    recruit_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Admin endpoint to delete a recruitment posting."""
    success = await recruit_service.delete_recruitment(db, recruit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return {"success": True, "message": "Recruitment deleted"}
