from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Header
from typing import List, Optional
from common.database import get_async_db
from common.config import settings

router = APIRouter()

@router.post(
    "/crawl", 
    status_code=202,
    summary="채용 공고 크롤링 트리거",
    description="배경 작업으로 채용 공고 크롤링을 시작합니다. 관리자 비밀번호가 필요합니다."
)
def trigger_crawling(
    background_tasks: BackgroundTasks, 
    x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret")
):
    """
    Trigger the recruitment crawling process in the background.
    Requires a secret key for basic security.
    """
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    from app.services.job_service import job_service
    # Trigger the scraping job
    success = job_service.trigger_recommendation_update()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger crawling job (Infrastructure error)")
        
    return {"message": "Crawling job triggered successfully"}

@router.post(
    "/fast-crawl", 
    status_code=202,
    summary="급속 채용 공고 크롤링 트리거 (1페이지, 1개)",
    description="빠른 테스트를 위해 1페이지에서 1개의 공고만 크롤링합니다. 관리자 비밀번호가 필요합니다."
)
def trigger_fast_crawling(
    background_tasks: BackgroundTasks, 
    x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret")
):
    """
    Trigger a limited crawling process (1 page, 1 item) for testing.
    """
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    from app.services.job_service import job_service
    # Trigger with extra parameters
    success = job_service.trigger_recommendation_update(pages=1, limit=1)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger fast crawling job")
        
    return {"message": "Fast crawling job triggered successfully (1 page, 1 item)"}

@router.delete(
    "/clear", 
    status_code=200,
    summary="데이터베이스 초기화 (DROP & RECREATE)",
    description="모든 테이블을 삭제하고 다시 생성합니다. 스키마 변경 시 유용하지만 모든 데이터가 삭제되니 주의하십시오."
)
async def clear_database(
    x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret"),
    db = Depends(get_async_db)  # Use dependency for session
):
    """
    Clear ALL database tables by DROPPING them and Re-creating them.
    This ensures schema updates (like JSON -> Vector) are applied.
    WARNING: This will delete everything!
    """
    # Security check
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    try:
        from sqlalchemy import text
        from common.database import async_engine, Base
        import common.models # Ensure models are loaded

        # 1. Get all tables in the public schema except alembic_version and spatial_ref_sys
        get_tables_query = text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
              AND tablename <> 'alembic_version'
        """)
        result = await db.execute(get_tables_query)
        tables = [row[0] for row in result.all()]
        
        if tables:
            # 2. Drop tables with CASCADE
            for t in tables:
                await db.execute(text(f'DROP TABLE IF EXISTS public."{t}" CASCADE'))
            await db.commit()
        
        # 3. Re-create tables with updated schema
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        return {
            "message": "All database tables dropped and re-created successfully.",
            "dropped_tables": tables,
            "schema_updated": True
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset DB: {str(e)}")

@router.post(
    "/generate-embeddings",
    status_code=202,
    summary="공고 임베딩 일괄 생성 (Job 트리거)",
    description="임베딩이 없는 모든 채용 공고에 대해 임베딩을 생성하는 Job을 트리거합니다. X-Admin-Secret 헤더 필요."
)
async def generate_embeddings(
    background_tasks: BackgroundTasks,
    x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret")
):
    """
    임베딩 생성 Job을 트리거합니다.
    X-Admin-Secret 헤더로 인증.
    """
    
    # 관리자 키 확인
    if x_admin_secret != settings.INTERNAL_API_SECRET:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    
    try:
        from app.services.job_service import job_service
        
        # Job 트리거 (recruit_indexing task가 임베딩 생성 포함)
        job_service.trigger_recruit_indexing()
        
        return {
            "success": True,
            "message": "임베딩 생성 Job이 트리거되었습니다.",
            "task": "recruit_indexing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job 트리거 실패: {str(e)}")

@router.post(
    "/fix-questions",
    status_code=202,
    summary="잘못된 질문 양식 수정 (Job 트리거)",
    description="한글 키(질문 등)를 사용하는 공고를 찾아 다시 크롤링하고 표준 양식으로 수정합니다. X-Admin-Secret 헤더 필요."
)
async def fix_questions(
    background_tasks: BackgroundTasks,
    limit: int = 20,
    x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret")
):
    """
    잘못된 질문 양식 수정 Job을 트리거합니다.
    """
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    try:
        from app.services.job_service import job_service
        job_service.trigger_fix_questions(limit=limit)
        
        return {
            "success": True,
            "message": f"질문 수정 Job이 트리거되었습니다. (Limit: {limit})",
            "task": "fix_questions"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job 트리거 실패: {str(e)}")

@router.post(
    "/deduplicate-questions",
    status_code=202,
    summary="자기소개서 문항 중복 제거 (Job 트리거)",
    description="데이터베이스의 모든 채용 공고를 순회하며 중복된 자기소개서 문항을 제거합니다. X-Admin-Secret 헤더 필요."
)
async def deduplicate_questions(
    background_tasks: BackgroundTasks,
    x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret")
):
    """
    중복 문항 제거 Job을 트리거합니다.
    """
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    try:
        from app.services.job_service import job_service
        job_service.trigger_deduplicate_questions()
        
        return {
            "success": True,
            "message": "자기소개서 문항 중복 제거 Job이 트리거되었습니다.",
            "task": "deduplicate_questions"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job 트리거 실패: {str(e)}")
