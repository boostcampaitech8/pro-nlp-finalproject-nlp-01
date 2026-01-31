from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from common.database import get_async_db
from common import schemas
from app.services import recruit_service
from app.services.portfolio_service import PortfolioService
from app.api import deps

from common import models
from app.api.rate_limit import ai_gen_limiter

router = APIRouter()

@router.get(
    "", 
    response_model=schemas.PortfolioListResponse,
    summary="포트폴리오 목록 조회",
    description="로그인한 사용자가 생성한 모든 포트폴리오(파일, GitHub, Notion 포함) 목록을 반환합니다."
)
async def list_portfolios(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
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
    service = PortfolioService(db)
    saved_portfolio = await service.save_verified_portfolio(current_user.id, portfolio)
    # Trigger background recommendation update
    background_tasks.add_task(recruit_service.run_bg_recalc_for_user, current_user.id)
    # Trigger background profile update
    background_tasks.add_task(job_service.trigger_job, task="profile_update", target_id=saved_portfolio.id)
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
    service = PortfolioService(db)
    return await service.create_portfolio_from_file(current_user.id, title, file, background_tasks)

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
    service = PortfolioService(db)
    return await service.create_portfolio_from_notion(current_user.id, payload.title, payload.source_url, background_tasks)

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
    service = PortfolioService(db)
    return await service.create_portfolio_from_github(current_user.id, payload.title, payload.source_url, background_tasks)

@router.get("/{portfolio_id}", response_model=schemas.PortfolioDetail)
async def get_portfolio(
    portfolio_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.patch("/{portfolio_id}", response_model=schemas.PortfolioDetail)
async def update_portfolio(
    portfolio_id: int,
    portfolio: schemas.PortfolioUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    service = PortfolioService(db)
    updated_portfolio = await service.update_portfolio(
        portfolio_id, current_user.id, portfolio.model_dump(exclude_unset=True)
    )
    if not updated_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found or unauthorized")
    
    # Trigger background recommendation update
    background_tasks.add_task(recruit_service.run_bg_recalc_for_user, current_user.id)
    return updated_portfolio

@router.delete("/{portfolio_id}")
@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
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
    service = PortfolioService(db)
    return await service.analyze_portfolio_file(current_user.id, file)

@router.patch("/{portfolio_id}/confirm", response_model=schemas.PortfolioDetail)
async def confirm_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Confirms AI analysis results and marks as COMPLETED."""
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Update status to COMPLETED
    portfolio.processing_status = models.ProcessingStatus.COMPLETED
    await db.commit()
    await db.refresh(portfolio)
    
    # Update recommendations and profile
    background_tasks = BackgroundTasks() # We need to inject BackgroundTasks if not present, but better to use job_service directly or request injection.
    # Wait, confirm_portfolio signature doesn't have background_tasks. Let's add it. 
    # Actually, simpler to just fire and forget via job_service directly if we don't want to change signature too much, 
    # BUT job_service.trigger_job is synchronous (encapsulates logic), so we can just call it.
    # Ideally should use BackgroundTasks for non-blocking HTTP response if possible, but let's change signature to be correct.
    # Since I cannot see the signature change here, I will modify the signature in a separate step or just call job_service if it returns fast (it spawns process or makes http call, so pretty fast).
    # Let's check imports. job_service is imported.
    from app.services.job_service import job_service
    job_service.trigger_job(task="recruit_update", target_id=current_user.id)
    job_service.trigger_job(task="profile_update", target_id=portfolio.id)
    
    return portfolio
