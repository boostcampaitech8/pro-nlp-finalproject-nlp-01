import logging
import traceback
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa
from langchain_core.documents import Document

from common import models

logger = logging.getLogger(__name__)

async def _get_portfolio_context(db: AsyncSession, portfolio_id: int):
    from common.models import Portfolio, User
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return None, None

    portfolio_data = {
        "project_name": portfolio.project_name,
        "description": portfolio.description,
        "tech_stack": portfolio.tech_stack,
        "role": portfolio.role,
        "period": portfolio.period
    }

    user_stmt = select(User).where(User.id == portfolio.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user:
        portfolio_data["user_summary"] = user.profile_summary
        portfolio_data["desired_job_title"] = user.desired_job_title

    return portfolio, portfolio_data

async def _search_candidates(db: AsyncSession, portfolio):
    from jobs.core.recruit.indexer import RecruitIndexer
    from common.models import PortfolioJobQuery, User
    
    indexer = RecruitIndexer()
    query_stmt = select(PortfolioJobQuery).where(PortfolioJobQuery.portfolio_id == portfolio.id)
    query_result = await db.execute(query_stmt)
    db_queries = query_result.scalars().all()

    all_candidates = []
    seen_ids = set()
    
    for db_q in db_queries:
        if not db_q.query_text: continue
        # Always use hybrid search to leverage both keywords and vector space
        initial_results = await indexer.search(db, db_q.query_text, k=10)
        
        for doc in initial_results:
            uid = doc.metadata.get('id')
            if uid and uid not in seen_ids:
                all_candidates.append(doc)
                seen_ids.add(uid)

    if not all_candidates:
        user_stmt = select(User).where(User.id == portfolio.user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        fallback_query = (user.desired_job_title if user else None) or portfolio.project_name or "개발자"
        logger.info(f"No candidates from queries, using fallback search: {fallback_query}")
        all_candidates = await indexer.search(db, fallback_query, k=10)

    return all_candidates

async def _save_recommendations(db: AsyncSession, user_id: int, portfolio_name: str, ai_recs: List[dict]):
    from common.models import Recommendation, Recruitment
    saved_count = 0
    for i, rec in enumerate(ai_recs):
        recruit_id = rec.get("id")
        if not recruit_id:
             r_stmt = select(Recruitment).where(
                 Recruitment.company == rec.get("company"),
                 Recruitment.title == rec.get("title")
             )
             r_obj = (await db.execute(r_stmt)).scalar_one_or_none()
             if r_obj: recruit_id = r_obj.id

        if recruit_id:
            # Use with_for_update() to handle concurrent triggers for the same user/job
            existing_stmt = select(Recommendation).where(
                Recommendation.user_id == user_id,
                Recommendation.recruitment_id == recruit_id
            ).with_for_update()
            existing_rec = (await db.execute(existing_stmt)).scalar_one_or_none()
            
            reasons_from_ai = rec.get('reason', [])
            if isinstance(reasons_from_ai, str):
                reasons_from_ai = [reasons_from_ai]
            
            new_reasons = [f"[{portfolio_name}] {r}" for r in reasons_from_ai]
            
            if existing_rec:
                existing_reasons = existing_rec.reason or []
                if not isinstance(existing_reasons, list): existing_reasons = [str(existing_reasons)]
                
                for nr in new_reasons:
                    if not any(r.startswith(f"[{portfolio_name}]") for r in existing_reasons):
                         existing_reasons.append(nr)
                
                existing_rec.reason = existing_reasons
            else:
                db.add(Recommendation(
                    user_id=user_id,
                    recruitment_id=recruit_id,
                    rank_order=100 + i,
                    reason=new_reasons
                ))
            saved_count += 1
    await db.commit()
    return saved_count

async def precompute_recommendations_for_portfolio(db: AsyncSession, portfolio_id: int):
    """
    Refactored orchestrator for recommendation pre-computation.
    """
    from jobs.core.recruit.matcher import RecruitMatcher
    
    # 1. Prepare Data
    portfolio, portfolio_data = await _get_portfolio_context(db, portfolio_id)
    if not portfolio:
        logger.error(f"Portfolio {portfolio_id} not found")
        return []

    # 2. Search Candidates
    all_candidates = await _search_candidates(db, portfolio)
    if not all_candidates:
        logger.info("No candidates found.")
        return []

    # 3. AI Rank and Reason
    matcher = RecruitMatcher()
    ai_recommendations = await matcher.rank_final_recommendations(portfolio_data, all_candidates)
    
    # 4. Save and Aggregate
    saved_count = await _save_recommendations(db, portfolio.user_id, portfolio.project_name, ai_recommendations)
    
    logger.info(f"Aggregated {saved_count} recommendations for Portfolio {portfolio_id}")
    return ai_recommendations

async def bulk_precompute_recommendations(db: AsyncSession):
    """
    Triggers pre-computation for all active portfolios in the database.
    Useful for background batch processing.
    """
    from common.models import Portfolio
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
    Rerank ALL recommendations for a user using their global profile.
    This provides a unified Top-N list of jobs relevant to the user's overall profile.
    """
    from jobs.core.recruit.matcher import RecruitMatcher
    from common.models import User, Recommendation, Recruitment
    
    logger.info(f"Starting global reranking for User {user_id}")
    
    # 1. Fetch User Profile
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if not user: return

    # Global Query: Use profile summary + desired job title
    global_query = f"{user.desired_job_title or '개발자'} {user.profile_summary or ''}"[:1000].strip()
    if not global_query:
        global_query = "개발자"

    # 2. Fetch ALL recommendations for this user
    rec_stmt = select(Recommendation, Recruitment).join(Recruitment).where(
        Recommendation.user_id == user_id
    )
    rec_result = await db.execute(rec_stmt)
    rows = rec_result.all()
    
    if not rows: return

    # 3. Convert to "Document-like" objects for Reranker
    candidates = []
    for rec_obj, recruitment in rows:
        content = (
            f"회사: {recruitment.company}\n"
            f"직무: {recruitment.title}\n"
            f"주요 업무: {recruitment.key_responsibilities}\n"
            f"자격 요건: {recruitment.required_qualifications}\n"
        )
        candidates.append(Document(page_content=content, metadata={"id": str(rec_obj.id)}))
    
    if not candidates: return

    # 4. Rerank using NCP
    matcher = RecruitMatcher()
    refined_results = await matcher.rerank_with_ncp(global_query, candidates, top_n=30)
    
    # 5. Update Rank Order
    for i, doc in enumerate(refined_results):
        try:
            rec_id = int(doc.metadata.get("id"))
            update_stmt = sa.update(Recommendation).where(Recommendation.id == rec_id).values(
                rank_order=i
            )
            await db.execute(update_stmt)
        except:
            continue
            
    await db.commit()
    logger.info(f"Global reranking completed for User {user_id}")

