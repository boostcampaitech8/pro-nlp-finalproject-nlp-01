import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, cast, String
import sqlalchemy as sa

from common import models
from common import schemas
from app.services.job_service import job_service

logger = logging.getLogger(__name__)

async def get_recruitments(db: AsyncSession, skip: int = 0, limit: int = 10, category: str = None, keyword: str = None, location: str = None, tech_stack: str = None, sort_by: str = 'latest'):
    CATEGORY_MAP = {
        'frontend': '프론트엔드',
        'backend': '서버/백엔드',
        'fullstack': '웹 풀스택',
        'ai': 'AI/ML/NLP',
        'data': '데이터',
        'mobile': '모바일',
        'devops': 'DevOps'
    }

    stmt = select(models.Recruitment)
    if category and category != 'all':
        mapped_category = CATEGORY_MAP.get(category, category)
        stmt = stmt.where(models.Recruitment.category == mapped_category)
    if keyword:
        stmt = stmt.where(
            models.Recruitment.title.ilike(f"%{keyword}%") | 
            models.Recruitment.company.ilike(f"%{keyword}%")
        )
    if location:
        stmt = stmt.where(models.Recruitment.location.ilike(f"%{location}%"))
    if tech_stack:
        skills = [s.strip() for s in tech_stack.split(',') if s.strip()]
        if skills:
            # Use JSON containment operator for PostgreSQL
            # models.Recruitment.tags.contains(skills) often works if mapped correctly
            # Or use explicit JSONB contains syntax via text or func
            # For simplicity and robustness with SQLite/Postgres:
            for skill in skills:
                stmt = stmt.where(models.Recruitment.tags.contains([skill]))
    
    if sort_by == 'popular':
        stmt = stmt.order_by(models.Recruitment.view_count.desc(), models.Recruitment.id.desc())
    else:
        stmt = stmt.order_by(models.Recruitment.id.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    count_stmt = select(func.count(models.Recruitment.id))
    if category and category != 'all':
        mapped_category = CATEGORY_MAP.get(category, category)
        count_stmt = count_stmt.where(models.Recruitment.category == mapped_category)
    if keyword:
        count_stmt = count_stmt.where(
            models.Recruitment.title.ilike(f"%{keyword}%") | 
            models.Recruitment.company.ilike(f"%{keyword}%")
        )
    if location:
        count_stmt = count_stmt.where(models.Recruitment.location.ilike(f"%{location}%"))
    if tech_stack:
        skills = [s.strip() for s in tech_stack.split(',') if s.strip()]
        if skills:
            for skill in skills:
                count_stmt = count_stmt.where(models.Recruitment.tags.contains([skill]))
    
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    return items, total

async def inc_view_count(db: AsyncSession, recruit_id: int):
    stmt = sa.update(models.Recruitment).where(models.Recruitment.id == recruit_id).values(
        view_count=models.Recruitment.view_count + 1
    )
    await db.execute(stmt)
    await db.commit()

async def get_recruitment(db: AsyncSession, recruit_id: int):
    stmt = select(models.Recruitment).where(models.Recruitment.id == recruit_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_ai_recommendations(db: AsyncSession, user_id: int, portfolio_id: Optional[int] = None):
    """
    Get pre-computed recruitment recommendations for a user.
    Aggregates all relevant recommendations across all user's portfolios.
    """
    from common.models import Recommendation, Recruitment
    
    # Simple query: join Recommendation and Recruitment for the user
    # Order by score desc (highest match first) or rank_order
    rec_stmt = select(Recommendation, Recruitment).join(Recruitment).where(
        Recommendation.user_id == user_id
    ).order_by(Recommendation.rank_order.asc())
    
    rec_result = await db.execute(rec_stmt)
    rows = rec_result.all()

    final_results = []
    for r_obj, recruitment in rows:
        reasons = r_obj.reason or []
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
            
        combined_reason = "• " + "\n• ".join(reasons) if len(reasons) > 1 else (reasons[0] if reasons else "")

        final_results.append({
            "id": recruitment.id,
            "title": recruitment.title,
            "company": recruitment.company,
            "category": recruitment.category,
            "location": recruitment.location,
            "tags": recruitment.tags or [], # Already a list of strings
            "deadline": recruitment.deadline.isoformat() if recruitment.deadline else None,
            "startDate": recruitment.start_date.isoformat() if recruitment.start_date else None,
            "reason": combined_reason
        })
    
    if not final_results and portfolio_id:
        logger.info(f"No recommendations for user {user_id}. Triggering job.")
        success = job_service.trigger_recommendation_update(user_id=user_id)
        if not success:
            return {"items": [], "status": "ERROR", "error": "Failed to trigger recommendation update"}
        return {"items": [], "status": "PROCESSING"}
    
    return {
        "items": final_results,
        "meta": {"total": len(final_results), "page": 1, "limit": 10, "totalPages": 1}
    }

async def run_bg_recalc_for_user(user_id: int):
    success = job_service.trigger_recommendation_update(user_id=user_id)
    if not success:
        logger.error(f"Failed to trigger background recommendation update for user {user_id}")

async def run_bg_inc_view_count(recruit_id: int):
    # This remains in backend as a light task or we can just call inc_view_count directly
    from common.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await inc_view_count(db, recruit_id)
