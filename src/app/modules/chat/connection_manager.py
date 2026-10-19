# 12b HITL - WebSocket Connection Manager & Redis Bridge
import asyncio
from collections import defaultdict
import json
import logging
from typing import Any
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from app.modules.chat.events import WSEvent, WSEventType
from app.modules.chat.redis_pubsub import (
    RedisPubSubManager,
    get_agent_alerts_channel,
    get_conversation_channel,
    get_redis_pubsub,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for visitors and agents, bridging them with Redis Pub/Sub."""
    # 12b HITL

    def __init__(self, pubsub_manager: RedisPubSubManager) -> None:
        self._pubsub_manager = pubsub_manager

        # Local in-memory active sockets
        # conversation_id -> set of active WebSockets
        self._conversation_sockets: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        # tenant_id -> set of active Agent WebSockets
        self._agent_sockets: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

        # Background Redis listener tasks
        # channel_name -> asyncio.Task
        self._active_listeners: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    # ==============================================================================
    # Visitor Connection Lifecycle
    # ==============================================================================

    async def connect_visitor(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        """Registers a visitor WebSocket and ensures a Redis channel listener is active."""
        if getattr(websocket.client_state, "name", None) != "CONNECTED":
            await websocket.accept()
        async with self._lock:
            self._conversation_sockets[conversation_id].add(websocket)
            channel = get_conversation_channel(tenant_id, conversation_id)
            if channel not in self._active_listeners:
                task = asyncio.create_task(
                    self._listen_redis_channel(channel, conversation_id=conversation_id)
                )
                self._active_listeners[channel] = task

        logger.info(
            "Visitor connected on WS: conv=%s (active sockets=%d)",
            conversation_id,
            len(self._conversation_sockets[conversation_id]),
        )

    async def disconnect_visitor(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        """Unregisters a visitor WebSocket and cancels channel listener if no sockets remain."""
        # 12b HITL
        async with self._lock:
            self._conversation_sockets[conversation_id].discard(websocket)
            if not self._conversation_sockets[conversation_id]:
                self._conversation_sockets.pop(conversation_id, None)
                channel = get_conversation_channel(tenant_id, conversation_id)
                listener = self._active_listeners.pop(channel, None)
                if listener:
                    listener.cancel()

        logger.info("Visitor disconnected from WS: conv=%s", conversation_id)

    # ==============================================================================
    # Agent Connection Lifecycle
    # ==============================================================================

    async def connect_agent(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        """Registers an agency agent socket and ensures an agent alerts listener is active."""
        if getattr(websocket.client_state, "name", None) != "CONNECTED":
            await websocket.accept()
        async with self._lock:
            self._agent_sockets[tenant_id].add(websocket)
            channel = get_agent_alerts_channel(tenant_id)
            if channel not in self._active_listeners:
                task = asyncio.create_task(
                    self._listen_redis_channel(channel, tenant_id=tenant_id)
                )
                self._active_listeners[channel] = task

        logger.info(
            "Agent %s connected on WS for tenant %s (active agents=%d)",
            user_id,
            tenant_id,
            len(self._agent_sockets[tenant_id]),
        )

    async def disconnect_agent(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        """Unregisters an agent WebSocket."""
        # 12b HITL
        async with self._lock:
            self._agent_sockets[tenant_id].discard(websocket)
            if not self._agent_sockets[tenant_id]:
                self._agent_sockets.pop(tenant_id, None)
                channel = get_agent_alerts_channel(tenant_id)
                listener = self._active_listeners.pop(channel, None)
                if listener:
                    listener.cancel()

        logger.info("Agent %s disconnected from WS for tenant %s", user_id, tenant_id)

    # ==============================================================================
    # Multi-Process Dispatcher & Redis Listener
    # ==============================================================================

    async def _listen_redis_channel(
        self,
        channel: str,
        *,
        conversation_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        """Subscribes to a Redis channel and fans out received events to local WebSockets."""
        # 12b HITL
        pubsub = self._pubsub_manager.create_pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue

                raw_data = raw_message["data"]
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")

                try:
                    event_data = json.loads(raw_data)
                except Exception:
                    continue

                # Broadcast to conversation sockets
                if conversation_id is not None:
                    await self._send_to_sockets(
                        self._conversation_sockets.get(conversation_id, set()), event_data
                    )

                # Broadcast to agency agent sockets
                if tenant_id is not None:
                    await self._send_to_sockets(
                        self._agent_sockets.get(tenant_id, set()), event_data
                    )
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Error in Redis pubsub listener for channel %s: %r", channel, exc)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def _send_to_sockets(
        self, sockets: set[WebSocket], data: dict[str, Any]
    ) -> None:
        """Sends JSON payload to all target sockets, safely purging broken ones."""
        # 12b HITL
        if not sockets:
            return

        dead_sockets: list[WebSocket] = []
        for ws in list(sockets):
            try:
                await ws.send_json(data)
            except (WebSocketDisconnect, RuntimeError):
                dead_sockets.append(ws)
            except Exception as exc:
                logger.warning("Error dispatching frame to socket: %r", exc)
                dead_sockets.append(ws)

        for dead in dead_sockets:
            sockets.discard(dead)

    # ==============================================================================
    # Event Broadcasting API
    # ==============================================================================

    async def broadcast_conversation_event(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, event: WSEvent
    ) -> None:
        """Publishes event to Redis so all workers distribute it to their WebSockets."""
        # 12b HITL
        await self._pubsub_manager.publish_conversation_event(tenant_id, conversation_id, event)

    async def broadcast_agent_alert(self, tenant_id: uuid.UUID, event: WSEvent) -> None:
        """Publishes alert to Redis agent channels."""
        # 12b HITL
        await self._pubsub_manager.publish_agent_alert(tenant_id, event)


_manager: ConnectionManager | None = None


# 12b HITL
def get_connection_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager(get_redis_pubsub())
    return _manager
