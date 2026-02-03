from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.database import get_async_db
from common import schemas
from common.exceptions import ResourceNotFoundError
from app.services.cover_letter_service import CoverLetterService
from app.services.ai_cover_letter_service import AICoverLetterService
from app.api import deps
from common import models
from app.api.rate_limit import ai_gen_limiter

router = APIRouter()

@router.get(
    "", 
    response_model=schemas.CoverLetterListResponse,
    summary="자기소개서 목록 조회",
    description="로그인한 사용자의 모든 자기소개서 목록을 조회합니다. 특정 채용 공고 ID로 필터링이 가능합니다."
)
async def list_cover_letters(
    recruit_id: Optional[int] = Query(None, description="필터링할 채용 공고 ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = CoverLetterService(db)
    items = await service.get_cover_letters(user_id=current_user.id, recruitment_id=recruit_id)
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
        raise ResourceNotFoundError("CoverLetter", cl_id)
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
        raise ResourceNotFoundError("CoverLetter", cl_id)
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
        raise ResourceNotFoundError("CoverLetter", cl_id)
    return {"success": True, "message": "Cover letter deleted"}

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
    from app.services.ai_cover_letter_service import ai_service
    return await ai_service.generate_cover_letter(db, current_user.id, req)

