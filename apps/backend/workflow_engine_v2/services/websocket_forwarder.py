"""Real WebSocket forwarder for events.

Subscribes to the EventBus and forwards events to WebSocket clients via HTTP calls to API Gateway.
Provides real-time workflow execution updates to connected clients.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Optional, Set
from urllib.parse import urljoin

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import ExecutionUpdateEvent

from .events import get_event_bus

logger = logging.getLogger(__name__)


class WebSocketForwarder:
    """Real WebSocket forwarder that sends events to API Gateway."""

    def __init__(
        self, send_callback: Optional[Callable[[ExecutionUpdateEvent], None]] = None
    ) -> None:
        """
        Initialize WebSocket forwarder.

        Args:
            send_callback: Optional custom callback for handling events
        """
        self._custom_callback = send_callback
        self._bus = get_event_bus()
        self._active_subscriptions: Set[str] = set()

        # Get API Gateway URL for WebSocket forwarding
        self._api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
        self._websocket_endpoint = "/api/v1/app/events/forward"

        # HTTP client for forwarding events
        self._client = httpx.AsyncClient(timeout=30.0)

        logger.info(f"WebSocket forwarder initialized, will forward to {self._api_gateway_url}")

    def start(self) -> None:
        """Start forwarding events to WebSocket clients."""
        self._bus.subscribe(self._forward_event)
        logger.info("WebSocket event forwarding started")

    def stop(self) -> None:
        """Stop forwarding events."""
        if hasattr(self, "_client"):
            asyncio.create_task(self._client.aclose())
        logger.info("WebSocket event forwarding stopped")

    async def _forward_event(self, event: ExecutionUpdateEvent) -> None:
        """Forward event to WebSocket clients via API Gateway."""
        try:
            # If custom callback provided, use it first
            if self._custom_callback:
                try:
                    self._custom_callback(event)
                except Exception as e:
                    logger.error(f"Custom callback error: {str(e)}")

            # Forward to API Gateway WebSocket handler
            await self._send_to_api_gateway(event)

        except Exception as e:
            logger.error(f"Error forwarding WebSocket event: {str(e)}")

    async def _send_to_api_gateway(self, event: ExecutionUpdateEvent) -> None:
        """Send event to API Gateway for WebSocket broadcast."""
        try:
            # Convert event to dictionary for JSON serialization
            event_data = {
                "event_type": event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type),
                "execution_id": event.execution_id,
                "timestamp": event.timestamp,
                "data": {
                    "node_id": event.data.node_id if event.data else None,
                    "execution_status": event.data.execution_status.value
                    if event.data and hasattr(event.data.execution_status, "value")
                    else None,
                    "partial_output": event.data.partial_output if event.data else None,
                    "error": event.data.error.__dict__ if event.data and event.data.error else None,
                    "user_input_request": event.data.user_input_request if event.data else None,
                },
            }

            # Send POST request to API Gateway
            url = urljoin(self._api_gateway_url, self._websocket_endpoint)
            response = await self._client.post(url, json=event_data)

            if response.status_code == 200:
                logger.debug(
                    f"Successfully forwarded event {event.event_type} for execution {event.execution_id}"
                )
            else:
                logger.warning(
                    f"API Gateway returned {response.status_code} when forwarding event: {response.text}"
                )

        except httpx.ConnectError:
            logger.warning(
                f"Could not connect to API Gateway at {self._api_gateway_url} for event forwarding"
            )
        except httpx.TimeoutException:
            logger.warning(f"Timeout forwarding event to API Gateway")
        except Exception as e:
            logger.error(f"Error sending event to API Gateway: {str(e)}")

    def subscribe_to_execution(self, execution_id: str) -> None:
        """Subscribe to events for a specific execution."""
        self._active_subscriptions.add(execution_id)
        logger.info(f"Subscribed to WebSocket events for execution {execution_id}")

    def unsubscribe_from_execution(self, execution_id: str) -> None:
        """Unsubscribe from events for a specific execution."""
        self._active_subscriptions.discard(execution_id)
        logger.info(f"Unsubscribed from WebSocket events for execution {execution_id}")

    def is_subscribed(self, execution_id: str) -> bool:
        """Check if subscribed to events for an execution."""
        return execution_id in self._active_subscriptions


# Global forwarder instance
_forwarder: Optional[WebSocketForwarder] = None


def get_websocket_forwarder() -> WebSocketForwarder:
    """Get or create the global WebSocket forwarder instance."""
    global _forwarder
    if _forwarder is None:
        _forwarder = WebSocketForwarder()
        _forwarder.start()
    return _forwarder


def start_websocket_forwarding() -> None:
    """Start the global WebSocket event forwarding."""
    forwarder = get_websocket_forwarder()
    logger.info("Global WebSocket event forwarding started")


def stop_websocket_forwarding() -> None:
    """Stop the global WebSocket event forwarding."""
    global _forwarder
    if _forwarder:
        _forwarder.stop()
        _forwarder = None
    logger.info("Global WebSocket event forwarding stopped")


__all__ = [
    "WebSocketForwarder",
    "get_websocket_forwarder",
    "start_websocket_forwarding",
    "stop_websocket_forwarding",
]
