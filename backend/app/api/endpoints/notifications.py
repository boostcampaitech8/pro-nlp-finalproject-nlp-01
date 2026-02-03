from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List
import os

from common.database import get_async_db
from common import schemas, models
from common.config import settings
from app.api import deps
from app.core.notifications import broadcaster

router = APIRouter()

@router.get("/events")
async def sse_notifications(
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    SSE endpoint for real-time notifications.
    """
    return StreamingResponse(
        broadcaster.subscribe(current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Important for Nginx/Cloud Run
        }
    )

@router.get("", response_model=schemas.NotificationListResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    List historical notifications. Uses Redis for unread count caching.
    """
    # 1. Fetch items
    stmt = select(models.Notification).where(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(50)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # 2. Get unread count from Redis
    unread_count = await broadcaster.get_unread_count(current_user.id)
    
    # 3. Fallback to DB if Redis is empty and sync it
    if unread_count is None:
        count_stmt = select(func.count()).select_from(models.Notification).where(
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == False
        )
        count_res = await db.execute(count_stmt)
        unread_count = count_res.scalar()
        await broadcaster.reset_unread_count(current_user.id, unread_count)
    
    return {"items": items, "unread_count": unread_count}

@router.patch("/{id}/read")
async def mark_as_read(
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # Check if actually exists and unread
    existing = await db.execute(
        select(models.Notification).where(
            models.Notification.id == id, 
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == False
        )
    )
    notif = existing.scalar_one_or_none()
    
    if notif:
        notif.is_read = True
        await db.commit()
        # Decrement Redis count
        await broadcaster.decr_unread_count(current_user.id)
        
    return {"status": "ok"}

@router.patch("/read-all")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    stmt = update(models.Notification).where(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).values(is_read=True)
    
    await db.execute(stmt)
    await db.commit()
    # Reset Redis count
    await broadcaster.reset_unread_count(current_user.id, 0)
    return {"status": "ok"}

@router.post("/trigger-internal")
async def trigger_notification_internal(
    payload: dict,
    x_internal_secret: str = Depends(deps.get_internal_secret_optional)
):
    """
    Internal endpoint called by Cloud Run Jobs to trigger real-time notification.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug logging
    masked_received = x_internal_secret[:3] + "***" if x_internal_secret and len(x_internal_secret) > 3 else "***"
    masked_expected = settings.INTERNAL_API_SECRET[:3] + "***" if len(settings.INTERNAL_API_SECRET) > 3 else "***"
    logger.info(f"Notification Internal Trigger: Received Secret={masked_received}, Expected={masked_expected}")

    if x_internal_secret != settings.INTERNAL_API_SECRET:
        logger.warning(f"Notification trigger auth failed. Received: {x_internal_secret}, Expected: {settings.INTERNAL_API_SECRET}")
        raise HTTPException(status_code=403, detail="Invalid internal secret")
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    notif_type = payload.get("type", "GENERAL")
    increment_unread = (notif_type != "REFRESH")
    
    await broadcaster.broadcast(user_id, payload, increment_unread=increment_unread)
    return {"status": "dispatched"}
