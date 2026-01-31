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
        media_type="text/event-stream"
    )

@router.get("", response_model=schemas.NotificationListResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    List historical notifications.
    """
    stmt = select(models.Notification).where(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(50)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # Count unread
    unread_stmt = select(func.count()).select_from(models.Notification).where(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    )
    unread_res = await db.execute(unread_stmt)
    unread_count = unread_res.scalar()
    
    return {"items": items, "unread_count": unread_count}

@router.patch("/{id}/read")
async def mark_as_read(
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    stmt = update(models.Notification).where(
        models.Notification.id == id,
        models.Notification.user_id == current_user.id
    ).values(is_read=True)
    
    await db.execute(stmt)
    await db.commit()
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
    
    await broadcaster.broadcast(user_id, payload)
    return {"status": "dispatched"}
