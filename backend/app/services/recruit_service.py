import traceback
import logging
from langchain_core.documents import Document
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import sqlalchemy as sa
from app.models import models
from app.schemas import schemas

logger = logging.getLogger(__name__)

async def get_recruitments(db: AsyncSession, skip: int = 0, limit: int = 10, category: str = None, keyword: str = None, location: str = None, tech_stack: str = None, sort_by: str = 'latest'):
    from sqlalchemy import or_, cast, String
    
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
            # Filter for tags containing ANY of the skills
            # Cast JSON to string and check if it contains "Skill" (quoted to avoid partial matches on simple text)
            # Note: This assumes tags are stored as a JSON list of strings ["Python", "Java"]
            conditions = [
                cast(models.Recruitment.tags, String).ilike(f'%"{skill}"%') 
                for skill in skills
            ]
            stmt = stmt.where(or_(*conditions))
    
    # Sorting
    if sort_by == 'popular':
        stmt = stmt.order_by(models.Recruitment.view_count.desc(), models.Recruitment.id.desc())
    else:
        stmt = stmt.order_by(models.Recruitment.id.desc())

    # Get items
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # Simple count query for efficiency
    count_stmt = select(func.count(models.Recruitment.id))
    if category and category != 'all':
        count_stmt = count_stmt.where(models.Recruitment.category == category)
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
            conditions = [
                cast(models.Recruitment.tags, String).ilike(f'%"{skill}"%') 
                for skill in skills
            ]
            count_stmt = count_stmt.where(or_(*conditions))
    
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    return items, total

async def inc_view_count(db: AsyncSession, recruit_id: int):
    """Increment the view count of a recruitment posting."""
    stmt = sa.update(models.Recruitment).where(models.Recruitment.id == recruit_id).values(
        view_count=models.Recruitment.view_count + 1
    )
    await db.execute(stmt)
    await db.commit()

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
    # 1. Fetch Portfolio or Use User Context
    if portfolio_id:
        stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            return {"items": []}
            
        rec_stmt = select(Recommendation, Recruitment).join(Recruitment).where(
            Recommendation.portfolio_id == portfolio.id
        ).order_by(Recommendation.rank_order)
    else:
        # Global View: Fetch all recommendations for the user
        rec_stmt = select(Recommendation, Recruitment).join(Recruitment).join(Portfolio).where(
            Portfolio.user_id == user_id
        ).order_by(Recommendation.rank_order)
    
    rec_result = await db.execute(rec_stmt)
    rows = rec_result.all()

    # Deduplicate by recruitment_id for global view
    seen_ids = set()
    unique_rows = []
    for r_obj, recruitment in rows:
        if recruitment.id not in seen_ids:
            unique_rows.append((r_obj, recruitment))
            seen_ids.add(recruitment.id)
            
    rows = unique_rows
    
    if not rows and portfolio_id:
        # Fallback only for specific portfolio request
        logger.info(f"No pre-computed recommendations for portfolio {portfolio.id}. Triggering initial computation.")
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
            "tags": recruitment.tags,
            "deadline": recruitment.deadline.isoformat() if recruitment.deadline else None,
            "startDate": recruitment.start_date.isoformat() if recruitment.start_date else None,
            "reason": rec_obj.reason
        }
        final_results.append(item)
    
    return {
        "items": final_results,
        "meta": {
            "total": len(final_results),
            "page": 1,
            "limit": 10,
            "totalPages": 1
        }
    }

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
        "project_name": portfolio.project_name,
        "description": portfolio.description,
        "tech_stack": portfolio.tech_stack,
        "role": portfolio.role,
        "period": portfolio.period
    }
    
    # Add User context if available
    from app.models.models import User
    user_stmt = select(User).where(User.id == portfolio.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user:
        portfolio_data["user_summary"] = user.profile_summary
        portfolio_data["desired_job_title"] = user.desired_job_title

    matcher = RecruitMatcher()
    indexer = RecruitIndexer()

    # 1. Fetch Job Queries and Search
    from app.models.models import PortfolioJobQuery
    query_stmt = select(PortfolioJobQuery).where(PortfolioJobQuery.portfolio_id == portfolio.id)
    query_result = await db.execute(query_stmt)
    db_queries = query_result.scalars().all()

    all_candidates = []
    seen_ids = set()
    
    for db_q in db_queries:
        if not db_q.query_text: continue
        if db_q.embedding is not None:
             # Use pre-calculated embedding directly
             initial_results = await indexer.search_by_vector(db, db_q.embedding, k=3)
        else:
             # Fallback: Generate embedding and search
             initial_results = await indexer.search(db, db_q.query_text, k=3)
        
        # Optimization: Skip local reranking to reduce API calls. 
        # We rely on Vector Score for initial candidate selection (Top 10)
        # and then use Global Reranker for final ordering.
        refined_results = initial_results 
        
        for doc in refined_results:
            uid = doc.metadata.get('id')
            if uid and uid not in seen_ids:
                all_candidates.append(doc)
                seen_ids.add(uid)

    if not all_candidates:
        # Fallback if no specific queries: use user context or project name
        fallback_query = (user.desired_job_title if user else None) or portfolio.project_name or "개발자"
        initial_results = await indexer.search(db, fallback_query, k=10)
        all_candidates = initial_results

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
                score=rec.get("score"),
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

async def global_rerank_recommendations(db: AsyncSession, user_id: int):
    """
    Rerank ALL recommendations across all portfolios for a user using their global profile.
    This provides a unified Top-N list of jobs relevant to the user's overall profile.
    """
    from app.core.recruit.matcher import RecruitMatcher
    from app.models.models import User, Portfolio, Recommendation, Recruitment
    
    # 1. Fetch User Profile
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if not user: return

    # Global Query: Use profile summary + desired job title
    global_query = ""
    if user.profile_summary:
        global_query = f"{user.desired_job_title or '개발자'} {user.profile_summary}"[:500]
    
    # Fallback to latest portfolio if user profile is empty
    if not global_query or len(global_query) < 10:
        port_stmt = select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc()).limit(1)
        port_res = await db.execute(port_stmt)
        latest_port = port_res.scalar_one_or_none()
        
        if latest_port:
            techs = ""
            if latest_port.tech_stack:
                # Handle JSON list or string
                if isinstance(latest_port.tech_stack, list):
                    techs = ", ".join(latest_port.tech_stack)
                else:
                    techs = str(latest_port.tech_stack)
                    
            global_query = f"{latest_port.role or '개발자'} {techs} {latest_port.description or ''}"[:500]
    
    if not global_query:
        global_query = "개발자"

    # 2. Fetch ALL existing recommendations for this user
    # Join Portfolio to filter by user_id
    rec_stmt = select(Recommendation, Recruitment).join(Portfolio).join(Recruitment).where(
        Portfolio.user_id == user_id
    )
    rec_result = await db.execute(rec_stmt)
    rows = rec_result.all()
    
    if not rows: return

    # 3. Convert to "Document-like" objects for Reranker
    # We use Recommendation ID as the "id" for mapping back
    candidates = []
    rec_map = {} # Map RecID -> Recommendation Object
    
    seen_recruit_ids = set()
    
    for rec_obj, recruitment in rows:
        # Avoid duplicate recruitments if multiple portfolios recommend the same job
        # But wait, we want to rerank specific (Portfolio, Recruitment) pairs?
        # User wants "Global List".
        # If Job A is recommended by P1 and P2, we should probably pick the best one or deduplicate.
        # Let's deduplicate by Recruitment ID for the global view logic.
        if recruitment.id in seen_recruit_ids:
            continue
        seen_recruit_ids.add(recruitment.id)
        
        rec_map[rec_obj.id] = rec_obj
        
        # Build content for reranker
        content = (
            f"회사: {recruitment.company}\n"
            f"직무: {recruitment.title}\n"
            f"주요 업무: {recruitment.key_responsibilities}\n"
            f"자격 요건: {recruitment.required_qualifications}\n"
        )
        
        doc = Document(page_content=content, metadata={"id": str(rec_obj.id)})
        candidates.append(doc)
    
    if not candidates: return

    # 4. Rerank using NCP
    matcher = RecruitMatcher()
    refined_results = await matcher.rerank_with_ncp(global_query, candidates, top_n=20)
    
    # 5. Update Rank Order
    # First, set all ranks to a high number (e.g. 999) to "hide" unranked ones
    # Or we can just update the ones returned by Reranker.
    
    # Let's update rank for the winners.
    for i, doc in enumerate(refined_results):
        try:
            rec_id = int(doc.metadata.get("id"))
            # Update this recommendation record
            update_stmt = sa.update(Recommendation).where(Recommendation.id == rec_id).values(rank_order=i)
            await db.execute(update_stmt)
        except:
            continue
            
    await db.commit()

async def trigger_user_recommendation_update(db: AsyncSession, user_id: int):
    """
    Helper to trigger recommendation update for a user's latest portfolio.
    Used in background tasks.
    And now triggers Global Reranking at the end.
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
            
            # Trigger Global Rerank
            logger.info(f"Triggering Global Rerank for User {user_id}")
            await global_rerank_recommendations(db, user_id)
            
        else:
            logger.info(f"No portfolio found for User {user_id} to update recommendations.")
            
    except Exception as e:
        logger.error(f"Background recommendation update failed for User {user_id}: {e}")
        logger.error(traceback.format_exc())

async def run_bg_recalc_for_user(user_id: int):
    """
    Standalone background task entry point.
    Creates a new DB session and triggers recommendation update.
    """
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await trigger_user_recommendation_update(db, user_id)

async def run_bg_inc_view_count(recruit_id: int):
    """
    Standalone background task to increment view count.
    Creates its own DB session to avoid "Session is closed" errors.
    """
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            await inc_view_count(db, recruit_id)
        except Exception as e:
            logger.error(f"Failed to increment view count for {recruit_id}: {e}")
