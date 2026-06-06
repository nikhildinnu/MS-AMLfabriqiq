import os
import time

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    conn_str = os.getenv("EVENT_HUB_CONNECTION_STRING", "")
    has_event_hub = bool(conn_str) and "YOUR_NAMESPACE" not in conn_str
    uptime = int(time.time() - request.app.state.start_time)

    from datetime import datetime, timezone
    return {
        "status": "ok",
        "service": "AML Event Injector",
        "version": "1.0.0",
        "mode": "LIVE" if has_event_hub else "DEMO",
        "eventHub": os.getenv("EVENT_HUB_NAME", "not-configured"),
        "uptime": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
