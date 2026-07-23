"""Hub in-process (+ Redis opcional) para feed SSE de Alertas (ADR 0022)."""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
from typing import Any

logger = logging.getLogger(__name__)

REDIS_CHANNEL = "limen:alerts"


class AlertHub:
    """Pub/sub local thread-safe para assinantes SSE no processo da API."""

    def __init__(self) -> None:
        self._subs: list[queue.Queue[dict[str, Any]]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        q: queue.Queue[dict[str, Any]] = queue.Queue()
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def publish_local(self, event: str, data: dict[str, Any]) -> None:
        message = {"event": event, "data": data}
        with self._lock:
            subscribers = list(self._subs)
        for sub in subscribers:
            sub.put(message)


_hub: AlertHub | None = None
_redis_bridge_started = False
_redis_bridge_lock = threading.Lock()


def get_alert_hub() -> AlertHub:
    global _hub
    if _hub is None:
        _hub = AlertHub()
    return _hub


def reset_alert_hub() -> None:
    """Reinicia hub (testes). Não derruba a thread Redis se já existir."""
    global _hub
    _hub = AlertHub()


def publish_alert_event(event: str, data: dict[str, Any]) -> None:
    """Publica localmente e, se possível, no Redis (worker → API)."""
    get_alert_hub().publish_local(event, data)
    _try_redis_publish(event, data)


def _try_redis_publish(event: str, data: dict[str, Any]) -> None:
    try:
        from redis import Redis

        from app.outbox.rq_client import redis_url

        client = Redis.from_url(redis_url(), socket_connect_timeout=0.5)
        client.publish(
            REDIS_CHANNEL,
            json.dumps({"event": event, "data": data}, default=str),
        )
    except Exception:  # noqa: BLE001 — fail-open (CI/demo sem Redis)
        logger.debug("Redis publish de Alerta indisponível", exc_info=True)


def ensure_redis_bridge_started() -> None:
    """Fan-out Redis → hub local (API). Idempotente; fail-open sem Redis."""
    global _redis_bridge_started
    with _redis_bridge_lock:
        if _redis_bridge_started:
            return
        _redis_bridge_started = True

    def _listen() -> None:
        try:
            from redis import Redis

            from app.outbox.rq_client import redis_url

            client = Redis.from_url(redis_url(), socket_connect_timeout=1.0)
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(REDIS_CHANNEL)
            for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message.get("data")
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                payload = json.loads(raw)
                get_alert_hub().publish_local(payload["event"], payload["data"])
        except Exception:  # noqa: BLE001
            logger.debug("Bridge Redis SSE encerrada/indisponível", exc_info=True)

    threading.Thread(target=_listen, name="limen-alerts-redis", daemon=True).start()


def sse_heartbeat_seconds() -> float:
    raw = os.getenv("LIMEN_SSE_HEARTBEAT_SECONDS", "15")
    try:
        return max(0.05, float(raw))
    except ValueError:
        return 15.0
