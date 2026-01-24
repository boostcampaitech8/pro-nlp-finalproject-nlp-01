from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas import schemas
from app.services import recruit_service

router = APIRouter()

@router.get("/", response_model=dict)
async def list_recruits(
    page: int = 1, 
    limit: int = 10, 
    category: Optional[str] = None, 
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    skip = (page - 1) * limit
    items, total = recruit_service.get_recruitments(
        db, skip=skip, limit=limit, category=category, keyword=keyword, location=location
    )
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total > 0 else 0
        }
    }

@router.get("/{recruit_id}", response_model=schemas.Recruitment)
async def get_recruit(recruit_id: int, db: Session = Depends(get_db)):
    db_recruit = recruit_service.get_recruitment(db, recruit_id)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return db_recruit

@router.post("/", response_model=schemas.Recruitment, status_code=201)
async def create_recruit(recruit: schemas.RecruitmentCreate, db: Session = Depends(get_db)):
    """Admin endpoint to create a new recruitment posting."""
    return recruit_service.create_recruitment(db, recruit)

@router.put("/{recruit_id}", response_model=schemas.Recruitment)
async def update_recruit(recruit_id: int, recruit: schemas.RecruitmentCreate, db: Session = Depends(get_db)):
    """Admin endpoint to update a recruitment posting."""
    db_recruit = recruit_service.update_recruitment(db, recruit_id, recruit)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return db_recruit

@router.delete("/{recruit_id}")
async def delete_recruit(recruit_id: int, db: Session = Depends(get_db)):
    """Admin endpoint to delete a recruitment posting."""
    success = recruit_service.delete_recruitment(db, recruit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return {"success": True, "message": "Recruitment deleted"}
