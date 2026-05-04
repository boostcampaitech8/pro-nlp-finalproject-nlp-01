from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.database import get_async_db
from common import schemas

from app.api import deps
from common import models
from app.api.rate_limit import ai_gen_limiter
from app.services.cover_letter_service import CoverLetterService
from app.services.ai_cover_letter_service import ai_service


router = APIRouter()

@router.get(
    "", 
    response_model=List[schemas.CoverLetter], # Changed response_model
    summary="자기소개서 목록 조회",
    description="로그인한 사용자의 모든 자기소개서 목록을 조회합니다. 특정 채용 공고 ID로 필터링이 가능합니다."
)
async def list_cover_letters(
    recruitment_id: Optional[int] = Query(None, description="필터링할 채용 공고 ID"), # Changed recruit_id to recruitment_id
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    # Changed logic to directly return the result
    return await service.get_cover_letters(current_user.id, recruitment_id)

@router.post("", response_model=schemas.CoverLetterDetail, status_code=201)
async def create_cover_letter_placeholder( # Renamed function
    cl_req: schemas.CoverLetterCreate, # Changed schema type
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Manually create a cover letter (placeholder)""" # Added docstring
    service = CoverLetterService(db)
    # Changed logic to assign user_id directly
    cl_req.user_id = current_user.id
    return await service.create_cover_letter(cl_req)

@router.get("/{cl_id}", response_model=schemas.CoverLetterDetail)
async def get_cover_letter(
    cl_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    db_cl = await service.get_cover_letter(cl_id, current_user.id)
    if not db_cl:
        raise HTTPException(status_code=404, detail="Cover letter not found") # Changed exception
    return db_cl

@router.patch("/{cl_id}", response_model=schemas.CoverLetterDetail)
async def update_cover_letter(
    cl_id: int, 
    data: dict, # Changed schema type to dict
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    updated_cl = await service.update_cover_letter( # Changed variable name
        cl_id, current_user.id, data # Changed argument
    )
    if not updated_cl: # Changed variable name
        raise HTTPException(status_code=404, detail="Cover letter not found") # Changed exception
    return updated_cl # Changed variable name

@router.delete("/{cl_id}")
async def delete_cover_letter(
    cl_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    success = await service.delete_cover_letter(cl_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Cover letter not found") # Changed exception
    return {"success": True, "message": "Cover letter deleted"}

@router.get("/{cl_id}/versions", response_model=List[schemas.CoverLetterVersion])
async def list_cover_letter_versions(
    cl_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Retrieves version history for a specific cover letter."""
    service = CoverLetterService(db)
    return await service.get_cover_letter_versions(cl_id, current_user.id)

@router.patch("/{cl_id}/confirm", response_model=schemas.CoverLetterDetail)
async def confirm_cover_letter(
    cl_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Marks a cover letter as COMPLETED after user review."""
    service = CoverLetterService(db)
    cl = await service.get_cover_letter(cl_id, current_user.id)
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    cl.processing_status = models.ProcessingStatus.COMPLETED
    await db.commit()
    await db.refresh(cl)
    return cl

@router.post(
    "/generate", 
    response_model=schemas.CoverLetterSummary,
    status_code=201,
    summary="AI 자기소개서 생성 시작",
    description="HyperCLOVA X를 사용하여 맞춤형 자기소개서를 생성합니다. 생성은 백그라운드에서 진행되며, Rate Limit(분당 5회)이 적용됩니다.",
    responses={
        429: {"description": "Too many requests. AI generation limit exceeded."},
        400: {"description": "Invalid recruitment ID or question data."}
    }
)
async def generate_cover_letter(
    request: Request,
    req: schemas.CoverLetterGenerateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Generates a cover letter using AI (HyperCLOVA X).
    """
    await ai_gen_limiter.check(request)
    return await ai_service.generate_cover_letter(db, current_user.id, req)

@router.post(
    "/items/{item_id}/refine",
    response_model=schemas.CoverLetterItemDetail,
    summary="자소서 문항 소제목 추가 (Refine)",
    description="기존 작성된 자소서 문항의 답변을 분석하여 적절한 소제목을 추가하고 구조화합니다. (내용 유지)"
)
async def refine_cover_letter_item(
    item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Refines a specific cover letter item's content by adding subheadings.
    """
    return await ai_service.refine_cover_letter_item(db, item_id)

@router.post(
    "/items/{item_id}/headline",
    response_model=schemas.CoverLetterItemDetail,
    summary="자소서 문항 소제목 생성",
    description="자소서 문항의 답변 내용을 분석하여 매력적인 소제목을 생성하고 최상단에 추가합니다."
)
async def generate_headline_for_item(
    item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Generates a headline for a specific cover letter item.
    """
    return await ai_service.generate_headline_for_item(db, item_id)

