import time
from fastapi import Request, HTTPException, status
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, requests_limit: int, window_seconds: int):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.client_state: Dict[str, List[float]] = {}

    async def check(self, request: Request):
        # Use IP address as client identifier
        client_ip = request.client.host
        now = time.time()
        
        if client_ip not in self.client_state:
            self.client_state[client_ip] = [now]
            return

        # Filter out old requests
        self.client_state[client_ip] = [
            t for t in self.client_state[client_ip] 
            if now - t < self.window_seconds
        ]

        if len(self.client_state[client_ip]) >= self.requests_limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )

        self.client_state[client_ip].append(now)

# Pre-defined limiters for different cost levels
# AI Generation: 5 requests per minute
ai_gen_limiter = RateLimiter(requests_limit=5, window_seconds=60)
# General API: 100 requests per minute (Optional use)
general_limiter = RateLimiter(requests_limit=100, window_seconds=60)
