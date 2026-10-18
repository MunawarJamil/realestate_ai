"""Sliding-window rate limiter for public widget endpoints with Redis and in-memory fallback."""

import asyncio
from collections import defaultdict
import time

from fastapi import HTTPException, Request, status
import structlog

from app.workers.queue import _pool

logger = structlog.get_logger(__name__)

# Fallback in-memory rate limiting table: key -> list of UTC timestamps
_in_memory_timestamps: dict[str, list[float]] = defaultdict(list)
_in_memory_lock = asyncio.Lock()


class WidgetRateLimiter:
    """Sliding-window rate limiter for widget visitor operations."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, key: str) -> None:
        """Enforces rate limit for the specified key.

        Tries Redis first (via active pool); falls back to in-memory sliding window.
        Raises HTTPException(429) if exceeded.
        """
        now = time.time()
        redis_client = _pool

        if redis_client is not None:
            try:
                redis_key = f"rate_limit:widget:{key}"
                pipe = redis_client.pipeline()
                # Remove timestamps older than window
                pipe.zremrangebyscore(redis_key, 0, now - self.window_seconds)
                # Count remaining items
                pipe.zcard(redis_key)
                # Add current request
                pipe.zadd(redis_key, {str(now): now})
                # Set TTL
                pipe.expire(redis_key, self.window_seconds + 5)
                results = await pipe.execute()
                current_count = int(results[1])
                if current_count >= self.max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please wait a moment before sending another message.",
                    )
                return
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning("Redis rate limiter failed, falling back to in-memory: %r", exc)

        # In-memory fallback
        async with _in_memory_lock:
            cutoff = now - self.window_seconds
            valid_stamps = [t for t in _in_memory_timestamps[key] if t > cutoff]
            if len(valid_stamps) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please wait a moment before sending another message.",
                )
            valid_stamps.append(now)
            _in_memory_timestamps[key] = valid_stamps


# Reusable dependency instances
standard_rate_limiter = WidgetRateLimiter(max_requests=60, window_seconds=60)
chat_message_rate_limiter = WidgetRateLimiter(max_requests=25, window_seconds=60)


async def rate_limit_visitor(request: Request) -> None:
    """Dependency that rate limits based on visitor Authorization header or Client IP."""
    auth_header = request.headers.get("Authorization")
    client_ip = request.client.host if request.client else "unknown"
    key = auth_header if auth_header else f"ip:{client_ip}"
    await standard_rate_limiter.check(key)


async def rate_limit_chat_stream(request: Request) -> None:
    """Stricter rate limiting dependency for generative LLM completions and streaming."""
    auth_header = request.headers.get("Authorization")
    client_ip = request.client.host if request.client else "unknown"
    key = f"stream:{auth_header}" if auth_header else f"stream:ip:{client_ip}"
    await chat_message_rate_limiter.check(key)
