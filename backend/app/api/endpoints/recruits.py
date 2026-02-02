from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
from common.database import get_async_db
from common import schemas
from app.services import recruit_service
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
    location: Optional[str] = None,
    techStack: Optional[str] = None,
    sort: str = Query("latest", regex="^(latest|popular)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[models.User] = Depends(deps.get_current_user_optional)
):
    skip = (page - 1) * limit
    items, total = await recruit_service.get_recruitments(
        db, skip=skip, limit=limit, category=category, keyword=keyword, location=location, tech_stack=techStack, sort_by=sort
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
    return await recruit_service.get_ai_recommendations(db, current_user.id, portfolio_id)

@router.get("/{recruit_id}", response_model=schemas.Recruitment)
async def get_recruit(
    recruit_id: int, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    db_recruit = await recruit_service.get_recruitment(db, recruit_id)
    if not db_recruit:
        raise HTTPException(status_code=404, detail="Recruitment not found")
    
    # Increment view count in background
    background_tasks.add_task(recruit_service.run_bg_inc_view_count, recruit_id)
    
    return db_recruit

@router.post("", response_model=schemas.Recruitment, status_code=201)
async def create_recruit(
    recruit: schemas.RecruitmentCreate, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Admin endpoint to create a new recruitment posting."""
    return await recruit_service.create_recruitment(db, recruit)

@router.post("/trigger-index", status_code=202)
async def trigger_indexing(
    internal_secret: str = Depends(deps.get_internal_secret_optional)
):
    """
    Internal trigger for recruitment indexing (used by Cloud Scheduler).
    Authorized via X-Internal-Secret header.
    """
    from common.config import settings
    import logging
    logger = logging.getLogger(__name__)

    # Debug logging for 403 investigation
    logger.info(f"Trigger Index Auth Check:")
    logger.info(f"Received Secret Length: {len(internal_secret) if internal_secret else 'None'}")
    logger.info(f"Expected Secret Length: {len(settings.INTERNAL_API_SECRET)}")
    
    if internal_secret:
        masked_received = internal_secret[:3] + "***" if len(internal_secret) > 3 else "***"
        logger.info(f"Received Secret (Masked): {masked_received}")
    
    masked_expected = settings.INTERNAL_API_SECRET[:3] + "***" if len(settings.INTERNAL_API_SECRET) > 3 else "***"
    logger.info(f"Expected Secret (Masked): {masked_expected}")

    if internal_secret != settings.INTERNAL_API_SECRET:
        logger.warning(f"Internal secret mismatch. Received: {internal_secret}, Expected: {settings.INTERNAL_API_SECRET}") # Be careful with this in prod, but needed for debug
        raise HTTPException(status_code=403, detail="Not authorized for internal trigger")
        
    from app.services.job_service import job_service
    success = job_service.trigger_job(task="recruit_indexing") 
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger indexing job")
        
    return {"message": "Recruitment indexing job triggered via internal auth"}

@router.post(
    "/generate-embeddings",
    status_code=200,
    summary="공고 임베딩 일괄 생성",
    description="임베딩이 없는 모든 채용 공고에 대해 임베딩을 생성합니다. X-Admin-Secret 헤더 필요.",
    response_model=Dict
)
async def generate_embeddings(
    db: AsyncSession = Depends(get_async_db),
    x_admin_secret: Optional[str] = Header(None)
):
    """
    임베딩이 NULL인 모든 채용 공고에 대해 임베딩을 생성합니다.
    X-Admin-Secret 헤더로 인증.
    """
    import logging
    from sqlalchemy import select
    from jobs.core.portfolio.storage.supabase_vector_store import ManualRAG
    from common.config import settings
    
    logger = logging.getLogger(__name__)
    
    # 관리자 키 확인
    if x_admin_secret != settings.INTERNAL_API_SECRET:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    
    try:
        # ManualRAG 인스턴스 생성
        rag = ManualRAG()
        
        # 임베딩이 없는 공고 조회
        stmt = select(models.Recruitment).where(models.Recruitment.embedding == None)
        result = await db.execute(stmt)
        recruitments_to_embed = result.scalars().all()
        
        total_count = len(recruitments_to_embed)
        logger.info(f"Found {total_count} recruitments without embeddings")
        
        if total_count == 0:
            return {
                "success": True,
                "message": "모든 공고에 이미 임베딩이 있습니다.",
                "total": 0,
                "generated": 0
            }
        
        # 임베딩 생성
        generated_count = 0
        failed_count = 0
        
        for idx, recruitment in enumerate(recruitments_to_embed, 1):
            try:
                # 텍스트 조합
                text_parts = [
                    recruitment.company or "",
                    recruitment.title or "",
                    recruitment.category or "",
                    recruitment.key_responsibilities or "",
                    recruitment.required_qualifications or "",
                    recruitment.preferred_qualifications or ""
                ]
                combined_text = " ".join([p for p in text_parts if p]).strip()
                
                if combined_text:
                    # 임베딩 생성 (동기 함수)
                    import asyncio
                    loop = asyncio.get_event_loop()
                    embedding = await loop.run_in_executor(None, rag.get_embedding, combined_text)
                    
                    recruitment.embedding = embedding
                    generated_count += 1
                    
                    # 진행상황 로그
                    if generated_count % 10 == 0:
                        logger.info(f"Progress: {generated_count}/{total_count} embeddings generated")
                        
            except Exception as e:
                logger.error(f"Failed to generate embedding for recruitment {recruitment.id}: {e}")
                failed_count += 1
                continue
        
        # DB 커밋
        await db.commit()
        
        logger.info(f"Embedding generation complete. Generated: {generated_count}, Failed: {failed_count}")
        
        return {
            "success": True,
            "message": f"임베딩 생성 완료: {generated_count}개 성공, {failed_count}개 실패",
            "total": total_count,
            "generated": generated_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"임베딩 생성 실패: {str(e)}")

@router.post("/index", status_code=201)

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
