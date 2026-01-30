from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.database import get_async_db
from common import schemas
from app.services.cover_letter_service import CoverLetterService
from app.services.ai_cover_letter_service import AICoverLetterService
from app.api import deps
from common import models

router = APIRouter()

@router.get("", response_model=schemas.CoverLetterListResponse)
async def list_cover_letters(
    recruitId: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    items = await service.get_cover_letters(user_id=current_user.id, recruitment_id=recruitId)
    return {"items": items}

@router.post("", response_model=schemas.CoverLetterDetail, status_code=201)
async def create_cover_letter(
    cl: schemas.CoverLetterCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    # Convert Request schema to internal Create schema (adding user_id)
    cl_data = cl.model_dump()
    internal_cl = schemas.CoverLetterCreate(**cl_data, user_id=current_user.id)
    return await service.create_cover_letter(internal_cl)

@router.get("/{cl_id}", response_model=schemas.CoverLetterDetail)
async def get_cover_letter(
    cl_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    db_cl = await service.get_cover_letter(cl_id, current_user.id)
    if not db_cl:
        raise HTTPException(status_code=404, detail="Cover letter not found or unauthorized")
    return db_cl

@router.patch("/{cl_id}", response_model=schemas.CoverLetterDetail)
async def update_cover_letter(
    cl_id: int, 
    cl: schemas.CoverLetterUpdateRequest, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    db_cl = await service.update_cover_letter(
        cl_id, current_user.id, cl.model_dump(exclude_unset=True)
    )
    if not db_cl:
        raise HTTPException(status_code=404, detail="Cover letter not found or unauthorized")
    return db_cl

@router.delete("/{cl_id}")
async def delete_cover_letter(
    cl_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    success = await service.delete_cover_letter(cl_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Cover letter not found or unauthorized")
    return {"success": True, "message": "Cover letter deleted"}

@router.post("/generate", response_model=schemas.CoverLetterDetail)
async def generate_cover_letter(
    req: schemas.CoverLetterGenerateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Generates a cover letter using AI (HyperCLOVA X).
    """
    ai_service = AICoverLetterService()
    # Verify user ownership of portfolios if needed inside service or here
    return await ai_service.generate_cover_letter(db, current_user.id, req)

