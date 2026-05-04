from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
from common.database import get_async_db
from common import schemas
from app.api import deps
from common import models

router = APIRouter()

@router.get(
    "", 
    response_model=schemas.RecruitmentListResponse,
    summary="채용 공고 목록 조회",
    description="필터링 및 정렬 옵션에 따라 채용 공고 목록을 조회합니다. 로그인한 경우 백그라운드에서 추천 정보가 갱신됩니다."
)
async def list_recruits(
    background_tasks: BackgroundTasks,
    page: int = 1, 
    limit: int = 10, 
    category: Optional[str] = None, 
    keyword: Optional[str] = None,
    searchType: Optional[str] = Query("all", regex="^(all|title|company)$"),
    location: Optional[str] = None,
    techStack: Optional[str] = None,
    sort: str = Query("latest", regex="^(latest|popular)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[models.User] = Depends(deps.get_current_user_optional)
):
    from app.services import recruit_service
    from fastapi.responses import JSONResponse
    import traceback
    
    try:
        skip = (page - 1) * limit
        items, total = await recruit_service.get_recruitments(
            db, skip=skip, limit=limit, category=category, keyword=keyword, search_type=searchType, location=location, tech_stack=techStack, sort_by=sort
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
    except Exception as e:
        print(f"ERROR in list_recruits: {e}", flush=True)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Internal Error: {str(e)}", "trace": traceback.format_exc()})

@router.get(
    "/recommend", 
    response_model=Dict,
    summary="AI 맞춤 추천 채용 조회",
    description="사용자의 포트폴리오 분석 결과에 따라 가장 적합한 채용 공고들을 추천합니다."
)
async def get_recommendations(
    portfolio_id: Optional[int] = Query(None, description="특정 포트폴리오 기준 추천을 원할 경우 사용"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Get AI-powered recruitment recommendations based on user portfolio.
    """
    from app.services import recruit_service
    return await recruit_service.get_ai_recommendations(db, current_user.id, portfolio_id)

@router.get(
    "/{recruit_id}", 
    response_model=schemas.Recruitment,
    summary="채용 공고 상세 조회",
    description="특정 ID의 채용 공고 상세 내용을 조회합니다. 조회수가 자동으로 증가합니다."
)
async def get_recruit(
    recruit_id: int, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    from app.services import recruit_service
    db_recruit = await recruit_service.get_recruitment(db, recruit_id)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    
    # Increment view count in background
    background_tasks.add_task(recruit_service.run_bg_inc_view_count, recruit_id)
    
    return db_recruit

@router.post(
    "", 
    response_model=schemas.Recruitment, 
    status_code=201,
    summary="새 채용 공고 작성 (Admin)",
    description="관리자 권한을 가진 사용자가 새로운 채용 공고를 등록합니다."
)
async def create_recruit(
    recruit: schemas.RecruitmentCreate, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Admin endpoint to create a new recruitment posting."""
    from app.services import recruit_service
    return await recruit_service.create_recruitment(db, recruit)

@router.post(
    "/trigger-index", 
    status_code=202,
    summary="채용 공고 인덱싱 트리거 (Internal)",
    description="내부 서비스 또는 스케줄러를 위해 인덱싱 작업을 트리거합니다. X-Internal-Secret 헤더가 필요합니다."
)
async def trigger_indexing(
    internal_secret: str = Depends(deps.get_internal_secret_optional)
):
    """
    Internal trigger for recruitment indexing (used by Cloud Scheduler).
    Authorized via X-Internal-Secret header.
    """
    from common.config import settings
    from app.services.job_service import job_service
    import logging
    logger = logging.getLogger(__name__)

    if internal_secret != settings.INTERNAL_API_SECRET:
        raise HTTPException(status_code=403, detail="Not authorized for internal trigger")
        
    success = job_service.trigger_recruit_indexing() 
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger indexing job")
        
    return {"message": "Recruitment indexing job triggered via internal auth"}


@router.put(
    "/{recruit_id}", 
    response_model=schemas.Recruitment,
    summary="채용 공고 수정 (Admin)",
    description="특정 ID의 채용 공고 정보를 수정합니다. 관리자 권한이 필요합니다."
)
async def update_recruit(
    recruit_id: int, 
    recruit: schemas.RecruitmentCreate, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Admin endpoint to update a recruitment posting."""
    from app.services import recruit_service
    db_recruit = await recruit_service.update_recruitment(db, recruit_id, recruit)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    return db_recruit

@router.delete(
    "/{recruit_id}",
    summary="채용 공고 삭제 (Admin)",
    description="특정 ID의 채용 공고를 삭제합니다. 관리자 권한이 필요합니다."
)
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
