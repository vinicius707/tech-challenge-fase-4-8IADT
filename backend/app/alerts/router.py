"""Router SSE de Alertas (Épico 7 / T7.2)."""

from __future__ import annotations

import json
import queue
from typing import Annotated, Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.alerts.hub import (
    ensure_redis_bridge_started,
    get_alert_hub,
    sse_heartbeat_seconds,
)
from app.auth.deps import AccessTokenClaims, get_current_access_claims

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _sse_event_stream() -> Iterator[str]:
    hub = get_alert_hub()
    # Bridge Redis em thread daemon — não bloqueia o handshake SSE.
    ensure_redis_bridge_started()
    q = hub.subscribe()
    heartbeat = sse_heartbeat_seconds()
    try:
        yield ": connected\n\n"
        while True:
            try:
                message = q.get(timeout=heartbeat)
            except queue.Empty:
                yield ": ping\n\n"
                continue
            event = message["event"]
            data = json.dumps(message["data"], default=str, separators=(",", ":"))
            yield f"event: {event}\ndata: {data}\n\n"
    finally:
        hub.unsubscribe(q)


@router.get(
    "/stream",
    summary="Feed SSE de Alertas (fetch + Bearer; ADR 0022)",
    response_class=StreamingResponse,
)
def alerts_stream(
    _claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
) -> StreamingResponse:
    """Requer `Authorization: Bearer`. Não aceita token na query string."""
    return StreamingResponse(
        _sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
