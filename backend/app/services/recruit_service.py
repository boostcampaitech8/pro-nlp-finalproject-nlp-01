import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import sqlalchemy as sa
from app.models import models
from app.schemas import schemas

logger = logging.getLogger(__name__)

async def get_recruitments(db: AsyncSession, skip: int = 0, limit: int = 10, category: str = None, keyword: str = None, location: str = None):
    stmt = select(models.Recruitment)
    if category and category != 'all':
        stmt = stmt.where(models.Recruitment.category == category)
    if keyword:
        stmt = stmt.where(
            models.Recruitment.title.ilike(f"%{keyword}%") | 
            models.Recruitment.company.ilike(f"%{keyword}%")
        )
    if location:
        stmt = stmt.where(models.Recruitment.location.ilike(f"%{location}%"))
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Get items
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return items, total

async def get_recruitment(db: AsyncSession, recruit_id: int):
    stmt = select(models.Recruitment).where(models.Recruitment.id == recruit_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_recruitment(db: AsyncSession, recruit: schemas.RecruitmentCreate):
    db_recruit = models.Recruitment(**recruit.model_dump())
    db.add(db_recruit)
    await db.commit()
    await db.refresh(db_recruit)
    return db_recruit

async def update_recruitment(db: AsyncSession, recruit_id: int, recruit: schemas.RecruitmentCreate):
    db_recruit = await get_recruitment(db, recruit_id)
    if not db_recruit:
        return None
    for key, value in recruit.model_dump().items():
        setattr(db_recruit, key, value)
    await db.commit()
    await db.refresh(db_recruit)
    return db_recruit

async def delete_recruitment(db: AsyncSession, recruit_id: int):
    db_recruit = await get_recruitment(db, recruit_id)
    if not db_recruit:
        return False
    await db.delete(db_recruit)
    await db.commit()
    return True

async def get_ai_recommendations(db: AsyncSession, user_id: int, portfolio_id: Optional[int] = None):
    """
    Get pre-computed recruitment recommendations for a user.
    """
    from app.models.models import Portfolio, Recommendation, Recruitment
    
    # 1. Fetch Portfolio
    if portfolio_id:
        stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    else:
        stmt = select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc())
    
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        return {"items": []}

    # 2. Fetch Pre-computed Recommendations from DB
    rec_stmt = select(Recommendation, Recruitment).join(Recruitment).where(
        Recommendation.portfolio_id == portfolio.id
    ).order_by(Recommendation.rank_order)
    
    rec_result = await db.execute(rec_stmt)
    rows = rec_result.all()
    
    if not rows:
        logger.info(f"No pre-computed recommendations for portfolio {portfolio.id}. Triggering initial computation.")
        # Optional: In a real serverless env, we might return empty or trigger background.
        # Here we'll try to compute on-the-fly if missing (first time)
        recommendations = await precompute_recommendations_for_portfolio(db, portfolio.id)
        return {"items": recommendations}

    # 3. Format response
    final_results = []
    for rec_obj, recruitment in rows:
        item = {
            "id": recruitment.id,
            "title": recruitment.title,
            "company": recruitment.company,
            "category": recruitment.category,
            "location": recruitment.location,
            "reason": rec_obj.reason,
            "content": recruitment.content
        }
        final_results.append(item)
    
    return {"items": final_results}

async def precompute_recommendations_for_portfolio(db: AsyncSession, portfolio_id: int):
    """
    Run the full AI recommendation pipeline and save results to the DB.
    """
    from app.core.recruit.matcher import RecruitMatcher
    from app.core.recruit.indexer import RecruitIndexer
    from app.models.models import Portfolio, Recommendation, Recruitment
    
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()
    if not portfolio: return []

    portfolio_data = {
        "title": portfolio.title,
        "extracted_job_title": portfolio.extracted_job_title,
        "extracted_summary": portfolio.extracted_summary,
        "project_name": portfolio.project_name,
        "description": portfolio.description,
        "tech_stack": portfolio.tech_stack
    }

    matcher = RecruitMatcher()
    indexer = RecruitIndexer()

    # 1. Search and Rerank
    queries = await matcher.generate_search_queries(portfolio_data)
    all_candidates = []
    seen_ids = set()
    
    for q_key in ['query_a', 'query_b', 'query_c']:
        query_text = queries.get(q_key)
        if not query_text: continue
        initial_results = await indexer.search(query_text, k=10)
        refined_results = await matcher.rerank_with_ncp(query_text, initial_results, top_n=5)
        
        for doc in refined_results:
            uid = doc.metadata.get('unique_id') or doc.metadata.get('id')
            if uid and uid not in seen_ids:
                all_candidates.append(doc)
                seen_ids.add(uid)

    if not all_candidates:
        return []

    # 2. AI Re-rank and Reason
    recommendations = await matcher.rank_and_reason(portfolio_data, all_candidates)
    
    # 3. Save to Recommendation Table
    # Clear old ones first
    delete_stmt = sa.delete(Recommendation).where(Recommendation.portfolio_id == portfolio_id)
    await db.execute(delete_stmt)
    
    saved_results = []
    for i, rec in enumerate(recommendations):
        # We need the recruitment_id. Matcher returns metadata.
        # Assuming unique_id or some field maps to recruitment.id
        # Let's try to find it by company and title if id is not obvious
        recruit_id = rec.get("id")
        if not recruit_id:
             r_stmt = select(Recruitment).where(
                 Recruitment.company == rec.get("company"),
                 Recruitment.title == rec.get("title")
             )
             r_res = await db.execute(r_stmt)
             r_obj = r_res.scalar_one_or_none()
             if r_obj: recruit_id = r_obj.id

        if recruit_id:
            new_rec = Recommendation(
                portfolio_id=portfolio_id,
                recruitment_id=recruit_id,
                rank_order=i,
                reason=rec.get("reason", "")
            )
            db.add(new_rec)
            saved_results.append(rec)
    
    await db.commit()
    return saved_results

async def bulk_precompute_recommendations(db: AsyncSession):
    """
    Triggers pre-computation for all active portfolios in the database.
    Useful for background batch processing.
    """
    from app.models.models import Portfolio
    stmt = select(Portfolio.id)
    result = await db.execute(stmt)
    portfolio_ids = result.scalars().all()
    
    logger.info(f"Starting bulk pre-computation for {len(portfolio_ids)} portfolios...")
    for pid in portfolio_ids:
        try:
            await precompute_recommendations_for_portfolio(db, pid)
            logger.info(f"Pre-computed recommendations for portfolio {pid}")
        except Exception as e:
            logger.error(f"Failed to pre-compute for portfolio {pid}: {e}")
    
    return len(portfolio_ids)

async def trigger_user_recommendation_update(db: AsyncSession, user_id: int):
    """
    Helper to trigger recommendation update for a user's latest portfolio.
    Used in background tasks.
    """
    try:
        from app.models.models import Portfolio
        # Find latest portfolio
        stmt = select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if portfolio:
            logger.info(f"Triggering background recommendation update for User {user_id}, Portfolio {portfolio.id}")
            await precompute_recommendations_for_portfolio(db, portfolio.id)
        else:
            logger.info(f"No portfolio found for User {user_id} to update recommendations.")
            
    except Exception as e:
        logger.error(f"Background recommendation update failed for User {user_id}: {e}")

async def run_bg_recalc_for_user(user_id: int):
    """
    Standalone background task entry point.
    Creates a new DB session and triggers recommendation update.
    """
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await trigger_user_recommendation_update(db, user_id)
