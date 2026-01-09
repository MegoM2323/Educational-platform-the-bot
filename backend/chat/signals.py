import logging
import asyncio
from datetime import datetime
from weakref import WeakSet
from typing import Any

logger = logging.getLogger("chat.websocket")

active_consumers: WeakSet[Any] = WeakSet()


def register_consumer(consumer):
    """Register a consumer for graceful shutdown (weak reference)"""
    active_consumers.add(consumer)
    logger.debug(f"Consumer registered: total_active={len(active_consumers)}")


def unregister_consumer(consumer):
    """Unregister a consumer (weak reference - may already be garbage collected)"""
    active_consumers.discard(consumer)
    logger.debug(f"Consumer unregistered: total_active={len(active_consumers)}")


async def shutdown_all_connections():
    """Shutdown all active WebSocket connections gracefully"""
    logger.info(f"Shutting down {len(active_consumers)} active WebSocket connections")

    if not active_consumers:
        logger.info("No active consumers to shutdown")
        return

    # Create snapshot of consumers to avoid issues if WeakSet changes during iteration
    tasks = [consumer.graceful_shutdown() for consumer in list(active_consumers)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    failed = sum(1 for r in results if isinstance(r, Exception))
    logger.info(
        f"Graceful shutdown completed: total={len(active_consumers)}, failed={failed}"
    )
