import logging
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.models import Notification
from common.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def create_and_notify(
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        link: Optional[str] = None,
        notification_type: str = "GENERAL",
        target_id: Optional[int] = None
    ):
        """
        Consolidated helper to:
        1. Persist notification in DB.
        2. Trigger real-time broadcast via Backend internal API.
        """
        try:
            # 1. Persist to DB
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                link=link
            )
            db.add(notification)
            # We assume the caller commits later or we rely on session flush
            
            # 2. Trigger Real-time Event
            if not settings.BACKEND_URL or not str(settings.BACKEND_URL).startswith("http"):
                logger.warning(f"Skipping real-time notification broadcast: BACKEND_URL is empty or missing protocol ('{settings.BACKEND_URL}')")
                return

            target_url = f"{settings.BACKEND_URL}/api/notifications/trigger-internal"
            logger.info(f"Attempting to trigger notification at: {target_url}")
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        target_url,
                        json={
                            "user_id": user_id,
                            "type": notification_type,
                            "title": title,
                            "message": message,
                            "link": link,
                            "target_id": target_id
                        },
                        headers={
                            "X-Internal-Secret": settings.INTERNAL_API_SECRET
                        },
                        timeout=5.0
                    )
                    logger.info(f"Notification trigger response: {response.status_code} - {response.text}")
                except Exception as ex:
                    logger.warning(f"Failed to trigger real-time notification: {ex}")
            
            logger.info(f"Notification created and dispatched for User {user_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error in NotificationService: {e}")
