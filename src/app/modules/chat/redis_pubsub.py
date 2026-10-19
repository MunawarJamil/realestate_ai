# 12b HITL - Distributed Redis Pub/Sub Event Bus
from collections.abc import AsyncIterator
import json
import logging
from typing import Any
import uuid

import redis.asyncio as aioredis
from redis.asyncio.client import PubSub

from app.core.config import get_settings
from app.modules.chat.events import WSEvent

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


# 12b HITL
def get_conversation_channel(tenant_id: uuid.UUID | str, conversation_id: uuid.UUID | str) -> str:
    """Builds isolated Redis channel name for a specific conversation."""
    return f"tenant:{tenant_id}:conv:{conversation_id}"


# 12b HITL
def get_agent_alerts_channel(tenant_id: uuid.UUID | str) -> str:
    """Builds Redis channel name for agency-wide handoff alerts."""
    return f"tenant:{tenant_id}:agent_alerts"


class RedisPubSubManager:
    """Manages distributed event pub/sub across multi-process workers via Redis."""
    # 12b HITL

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def publish_event(self, channel: str, event: WSEvent) -> int:
        """Serializes and broadcasts WSEvent to a designated Redis channel."""
        try:
            payload_str = event.model_dump_json()
            return await self._redis.publish(channel, payload_str)
        except Exception as exc:
            logger.error("Failed to publish event to Redis channel %s: %r", channel, exc)
            return 0

    async def publish_conversation_event(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, event: WSEvent
    ) -> int:
        """Broadcasts event to all subscribers of a conversation."""
        channel = get_conversation_channel(tenant_id, conversation_id)
        return await self.publish_event(channel, event)

    async def publish_agent_alert(self, tenant_id: uuid.UUID, event: WSEvent) -> int:
        """Broadcasts alert to all connected agency agents."""
        channel = get_agent_alerts_channel(tenant_id)
        return await self.publish_event(channel, event)

    def create_pubsub(self) -> PubSub:
        """Spawns an async Redis pub/sub listener client."""
        return self._redis.pubsub()


# 12b HITL
async def init_redis_pubsub() -> RedisPubSubManager:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return RedisPubSubManager(_redis_client)


# 12b HITL
def get_redis_pubsub() -> RedisPubSubManager:
    if _redis_client is None:
        raise RuntimeError("Redis pub/sub client is not initialised. Call init_redis_pubsub().")
    return RedisPubSubManager(_redis_client)


# 12b HITL
async def close_redis_pubsub() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
