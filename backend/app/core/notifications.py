import asyncio
from typing import Dict, List, Optional
import json
import logging
from redis import asyncio as aioredis
from common.config import settings

logger = logging.getLogger(__name__)

class NotificationBroadcaster:
    """
    Redis-backed SSE broadcaster for real-time notifications.
    Supports multi-instance environments via Redis Pub/Sub.
    """
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        if not self.redis_url:
            logger.warning("REDIS_URL is not set. Real-time notifications might not work across instances.")
        
    async def get_redis(self):
        """Helper to get a redis connection"""
        if not self.redis_url:
            return None
        return await aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def subscribe(self, user_id: int):
        """
        Generator that subscribes to user-specific Redis channel and yields messages.
        """
        if not self.redis_url:
            # Fallback (or error) if no Redis
            logger.error("Cannot subscribe: Redis URL missing")
            return

        redis = await self.get_redis()
        pubsub = redis.pubsub()
        channel = f"notification:{user_id}"
        
        try:
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    # SSE format requires "data: " prefix and double newline
                    yield f"data: {message['data']}\n\n"
        except Exception as e:
            logger.error(f"Redis subscription error for user {user_id}: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await redis.close()

    async def broadcast(self, user_id: int, data: dict):
        """
        Publishes message to user-specific Redis channel.
        This works from ANY instance to ANY instance.
        """
        if not self.redis_url:
            logger.warning("Broadcasting skipped: No Redis URL")
            return

        channel = f"notification:{user_id}"
        payload = json.dumps(data, ensure_ascii=False)
        
        redis = await self.get_redis()
        try:
            # Publish to Redis
            # This returns number of subscribers passing the message
            # But in Pub/Sub, we just fire and forget usually, or trust Redis.
            await redis.publish(channel, payload)
            logger.info(f"Broadcasted to Redis channel {channel}: {payload}")
        except Exception as e:
            logger.error(f"Redis publish error for user {user_id}: {e}")
        finally:
            await redis.close()

# Singleton instance
broadcaster = NotificationBroadcaster()
