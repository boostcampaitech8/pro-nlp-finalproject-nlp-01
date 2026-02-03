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
    Uses a singleton connection pool for efficiency and stability.
    """
    _redis_pool: Optional[aioredis.Redis] = None

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        if not self.redis_url:
            logger.warning("REDIS_URL is not set. Real-time notifications might not work across instances.")

    async def get_redis(self) -> Optional[aioredis.Redis]:
        """
        Get or create a singleton Redis connection pool.
        """
        if not self.redis_url:
            return None
            
        if self._redis_pool is None:
            try:
                # Create a connection pool with keepalive to prevent timeouts
                self._redis_pool = aioredis.from_url(
                    self.redis_url, 
                    encoding="utf-8", 
                    decode_responses=True,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                logger.info("Initialized Redis connection pool for notifications")
            except Exception as e:
                logger.error(f"Failed to initialize Redis pool: {e}", exc_info=True)
                return None
        
        return self._redis_pool

    async def subscribe(self, user_id: int):
        """
        Generator that subscribes to user-specific Redis channel and yields messages.
        """
        if not self.redis_url:
            logger.error("Cannot subscribe: Redis URL missing")
            return

        redis = await self.get_redis()
        if not redis:
            logger.error("Cannot subscribe: Redis connection failed")
            return

        # For Pub/Sub, we need a dedicated connection or pubsub object
        # accessing .pubsub() on the client gets a pubsub instance
        pubsub = redis.pubsub()
        channel = f"notification:{user_id}"
        
        try:
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"Subscription cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Redis subscription error for user {user_id}: {e}", exc_info=True)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
                # Do NOT close the main redis pool here
            except Exception as e:
                logger.error(f"Error closing pubsub for user {user_id}: {e}")

    async def broadcast(self, user_id: int, data: dict, increment_unread: bool = True):
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
        if not redis:
            logger.error("Cannot broadcast: Redis connection failed")
            return

        try:
            await redis.publish(channel, payload)
            # Also increment unread count in Redis (if requested)
            if increment_unread:
                await self.incr_unread_count(user_id)
            logger.info(f"Broadcasted to Redis channel {channel}: {payload}")
        except Exception as e:
            logger.error(f"Redis publish error for user {user_id}: {e}", exc_info=True)

    async def incr_unread_count(self, user_id: int):
        redis = await self.get_redis()
        if not redis: return
        key = f"unread_count:{user_id}"
        await redis.incr(key)

    async def decr_unread_count(self, user_id: int, amount: int = 1):
        redis = await self.get_redis()
        if not redis: return
        key = f"unread_count:{user_id}"
        count = await redis.get(key)
        if count and int(count) > 0:
            await redis.decr(key, amount=amount)
            # Ensure it doesn't go below 0
            new_count = await redis.get(key)
            if new_count and int(new_count) < 0:
                await redis.set(key, 0)

    async def get_unread_count(self, user_id: int) -> Optional[int]:
        redis = await self.get_redis()
        if not redis: return None
        count = await redis.get(f"unread_count:{user_id}")
        return int(count) if count is not None else None

    async def reset_unread_count(self, user_id: int, count: int = 0):
        redis = await self.get_redis()
        if not redis: return
        await redis.set(f"unread_count:{user_id}", count)

    async def close(self):
        """Gracefully close the connection pool"""
        if self._redis_pool:
            await self._redis_pool.close()
            self._redis_pool = None
            logger.info("Closed Redis connection pool")

# Singleton instance
broadcaster = NotificationBroadcaster()
