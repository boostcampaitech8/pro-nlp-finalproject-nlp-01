from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from common.database import get_async_db
from common import schemas
from common.exceptions import ResourceNotFoundError
from app.api import deps
from common import models
from app.api.rate_limit import ai_gen_limiter

router = APIRouter()

@router.get(
    "", 
    response_model=schemas.PortfolioListResponse,
    summary="포트폴리오 목록 조회",
    description="""로그인한 사용자가 생성한 모든 포트폴리오 목록을 반환합니다.
    
    **지원하는 포트폴리오 타입:**
    - `github`: GitHub 저장소
    - `notion`: Notion 페이지
    - `blog`: 기술 블로그 (Velog, Tistory)
    - `file`: 업로드된 파일
    
    **처리 상태:**
    - `PENDING`: 분석 대기 중
    - `PROCESSING`: 분석 진행 중
    - `REVIEW_REQUIRED`: 사용자 검토 필요
    - `COMPLETED`: 분석 완료
    - `FAILED`: 분석 실패
    """,
    responses={
        200: {
            "description": "포트폴리오 목록 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "type": "github",
                                "source_url": "https://github.com/user/repo",
                                "project_name": "My Awesome Project",
                                "processing_status": "COMPLETED",
                                "created_at": "2024-01-01T00:00:00Z"
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "인증 실패"}
    }
)
async def list_portfolios(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    items = await service.get_portfolios(user_id=current_user.id)
    return {"items": items}

@router.post("", response_model=schemas.PortfolioDetail, status_code=201)
async def create_portfolio(
    portfolio: schemas.PortfolioCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    from app.services.portfolio_service import PortfolioService
    from app.services import recruit_service
    service = PortfolioService(db)
    saved_portfolio = await service.save_verified_portfolio(current_user.id, portfolio)
    # Trigger background recommendation update
    background_tasks.add_task(recruit_service.run_bg_recalc_for_user, current_user.id)
    # Trigger background profile update
    from app.services.job_service import job_service
    background_tasks.add_task(job_service.trigger_profile_update, saved_portfolio.id)
    return saved_portfolio

@router.post("/upload", response_model=schemas.PortfolioDetail, status_code=201)
async def upload_portfolio(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Upload a portfolio file (PDF/TXT/MD), save it, and trigger background extraction/refinement.
    """
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    return await service.create_portfolio_from_file(current_user.id, title, file)

@router.post("/notion", response_model=schemas.PortfolioDetail, status_code=201)
async def import_notion_portfolio(
    background_tasks: BackgroundTasks,
    payload: schemas.PortfolioCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Import portfolio from a Notion URL.
    """
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    return await service.create_portfolio_from_notion(current_user.id, payload.project_name, payload.source_url)

@router.post("/github", response_model=schemas.PortfolioDetail, status_code=201)
async def import_github_portfolio(
    background_tasks: BackgroundTasks,
    payload: schemas.PortfolioCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Import portfolio from a GitHub Repository or User Profile URL/ID.
    """
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    return await service.create_portfolio_from_github(current_user.id, payload.project_name, payload.source_url)

@router.post("/blog", response_model=schemas.PortfolioDetail, status_code=201)
async def import_blog_portfolio(
    background_tasks: BackgroundTasks,
    payload: schemas.PortfolioCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Import portfolio from a Technical Blog (Velog, Tistory).
    """
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    return await service.create_portfolio_from_blog(current_user.id, payload.project_name, payload.source_url)

@router.get("/blog/discover", response_model=List[dict])
async def discover_blog_posts(
    url: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Scrape a blog home/index page and return a list of post titles and URLs.
    """
    from app.services.portfolio_service import PortfolioService
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        service = PortfolioService(db)
        return await service.blog_extractor.discover_posts(url)
    except Exception as e:
        logger.error(f"Blog discovery failed for {url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [] # Return empty list instead of 500

@router.get("/{portfolio_id}", response_model=schemas.PortfolioDetail)
async def get_portfolio(
    portfolio_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id, current_user.id)
    if not portfolio:
        raise ResourceNotFoundError("Portfolio", portfolio_id)
    return portfolio

@router.patch("/{portfolio_id}", response_model=schemas.PortfolioDetail)
async def update_portfolio(
    portfolio_id: int,
    portfolio: schemas.PortfolioUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    from app.services.portfolio_service import PortfolioService
    from app.services import recruit_service
    service = PortfolioService(db)
    updated_portfolio = await service.update_portfolio(
        portfolio_id, current_user.id, portfolio
    )
    if not updated_portfolio:
        raise ResourceNotFoundError("Portfolio", portfolio_id)
    
    # Trigger background recommendation update
    background_tasks.add_task(recruit_service.run_bg_recalc_for_user, current_user.id)
    return updated_portfolio

@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    success = await service.delete_portfolio(portfolio_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")
    return {"success": True, "message": "Portfolio deleted"}

@router.post(
    "/analyze",
    summary="포트폴리오 URL 분석",
    description="GitHub 또는 Notion URL로부터 포트폴리오 정보를 소싱하여 AI 분석을 수행합니다. Rate Limit이 적용됩니다.",
    responses={429: {"description": "Analysis limit exceeded"}}
)
async def analyze_portfolio(
    request: Request,
    req: schemas.PortfolioAnalyzeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Real AI analysis of a portfolio source for preview."""
    await ai_gen_limiter.check(request)
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    return await service.analyze_portfolio_source(current_user.id, req.source, req.type)

@router.post("/analyze/file")
async def analyze_portfolio_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Real AI analysis of an uploaded file for preview."""
    await ai_gen_limiter.check(request)
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService(db)
    return await service.analyze_portfolio_file(current_user.id, file)

@router.patch("/{portfolio_id}/confirm", response_model=schemas.PortfolioDetail)
async def confirm_portfolio(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Confirms AI analysis results and marks as COMPLETED."""
    from app.services.portfolio_service import PortfolioService
    from app.services.job_service import job_service
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Update status to COMPLETED
    portfolio.processing_status = models.ProcessingStatus.COMPLETED
    await db.commit()
    await db.refresh(portfolio)
    
    # Update recommendations and profile in background (non-blocking)
    background_tasks.add_task(job_service.trigger_recommendation_update, current_user.id)
    background_tasks.add_task(job_service.trigger_profile_update, portfolio_id)
    
    return portfolio
