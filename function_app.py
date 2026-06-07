import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import azure.functions as func
from pydantic import ValidationError

from services.event_hub_service import send_events
from services.fabric_service import write_to_fabric
from validators.schemas import (
    AccountEvent,
    BatchRequest,
    CustomerEvent,
    MerchantEvent,
    TransactionEvent,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

STATIC_DIR = Path(__file__).parent / "static"
START_TIME = time.time()

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def ok(data: dict, code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(data, default=str),
        status_code=code,
        mimetype="application/json",
        headers=CORS,
    )


def err(msg: str, code: int = 400) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"error": msg}),
        status_code=code,
        mimetype="application/json",
        headers=CORS,
    )


def parse_body(req: func.HttpRequest):
    try:
        body = req.get_json()
        return body, None
    except (ValueError, TypeError):
        return None, err("Invalid JSON body", 400)


def _uid(prefix: str) -> str:
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"


def ts(offset_minutes: float = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return dt.isoformat()


# ── GET /api/health ───────────────────────────────────────────
@app.route(route="api/health", methods=["GET"])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    conn_str = os.getenv("EVENT_HUB_CONNECTION_STRING", "")
    has_event_hub = bool(conn_str) and "YOUR_NAMESPACE" not in conn_str
    fabric_uri = os.getenv("FABRIC_KUSTO_CLUSTER_URI", "")
    has_fabric = bool(fabric_uri) and "YOUR_EVENTHOUSE" not in fabric_uri

    return ok({
        "status": "ok",
        "service": "AML Event Injector",
        "version": "2.0.0",
        "mode": "LIVE" if has_event_hub else "DEMO",
        "eventHub": os.getenv("EVENT_HUB_NAME", "not-configured"),
        "fabric": "CONNECTED" if has_fabric else "NOT CONFIGURED",
        "uptime": int(time.time() - START_TIME),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ── POST /api/events/transaction ──────────────────────────────
@app.route(route="api/events/transaction", methods=["POST"])
async def transaction(req: func.HttpRequest) -> func.HttpResponse:
    body, error = parse_body(req)
    if error:
        return error
    try:
        validated = TransactionEvent(**body)
    except ValidationError as exc:
        return err(exc.errors()[0]["msg"], 422)

    event = validated.model_dump(exclude_none=False)
    event["txnId"] = event.get("txnId") or _uid("TXN")
    event["timestamp"] = event.get("timestamp") or ts()
    event["_injectedAt"] = ts()

    result = await send_events(event, "TRANSACTION")
    await write_to_fabric(event, "TRANSACTION")
    return ok({"success": True, "eventId": event["txnId"], **result})


# ── POST /api/events/customer ─────────────────────────────────
@app.route(route="api/events/customer", methods=["POST"])
async def customer(req: func.HttpRequest) -> func.HttpResponse:
    body, error = parse_body(req)
    if error:
        return error
    try:
        validated = CustomerEvent(**body)
    except ValidationError as exc:
        return err(exc.errors()[0]["msg"], 422)

    event = validated.model_dump(exclude_none=False)
    event["customerId"] = event.get("customerId") or _uid("CUST")
    event["onboardingDate"] = event.get("onboardingDate") or ts()
    event["_injectedAt"] = ts()

    result = await send_events(event, "CUSTOMER")
    await write_to_fabric(event, "CUSTOMER")
    return ok({"success": True, "eventId": event["customerId"], **result})


# ── POST /api/events/account ──────────────────────────────────
@app.route(route="api/events/account", methods=["POST"])
async def account(req: func.HttpRequest) -> func.HttpResponse:
    body, error = parse_body(req)
    if error:
        return error
    try:
        validated = AccountEvent(**body)
    except ValidationError as exc:
        return err(exc.errors()[0]["msg"], 422)

    event = validated.model_dump(exclude_none=False)
    event["accountId"] = event.get("accountId") or _uid("ACC")
    event["openDate"] = event.get("openDate") or ts()
    event["_injectedAt"] = ts()

    result = await send_events(event, "ACCOUNT")
    await write_to_fabric(event, "ACCOUNT")
    return ok({"success": True, "eventId": event["accountId"], **result})


# ── POST /api/events/merchant ─────────────────────────────────
@app.route(route="api/events/merchant", methods=["POST"])
async def merchant(req: func.HttpRequest) -> func.HttpResponse:
    body, error = parse_body(req)
    if error:
        return error
    try:
        validated = MerchantEvent(**body)
    except ValidationError as exc:
        return err(exc.errors()[0]["msg"], 422)

    event = validated.model_dump(exclude_none=False)
    event["merchantId"] = event.get("merchantId") or _uid("MERCH")
    event["_injectedAt"] = ts()

    result = await send_events(event, "MERCHANT")
    await write_to_fabric(event, "MERCHANT")
    return ok({"success": True, "eventId": event["merchantId"], **result})


# ── POST /api/events/batch ────────────────────────────────────
@app.route(route="api/events/batch", methods=["POST"])
async def batch(req: func.HttpRequest) -> func.HttpResponse:
    body, error = parse_body(req)
    if error:
        return error
    try:
        validated = BatchRequest(**body)
    except ValidationError as exc:
        return err(exc.errors()[0]["msg"], 422)

    enriched = [
        {**item.data, "_eventType": item.type, "_injectedAt": ts()}
        for item in validated.events
    ]
    result = await send_events(enriched, "BATCH")
    for item in enriched:
        await write_to_fabric(item, item.get("_eventType", "BATCH"))
    return ok({"success": True, **result})


# ── POST /api/events/seed/{pattern} ──────────────────────────
@app.route(route="api/events/seed/{pattern}", methods=["POST"])
async def seed(req: func.HttpRequest) -> func.HttpResponse:
    pattern = req.route_params.get("pattern", "")
    events: list = []
    label: str = ""

    if pattern == "structuring":
        label = "Structuring / Smurfing"
        from_acc = "ACC-STRUCT-042"
        amounts = [9800, 9500, 9200, 8900]
        events = [
            {
                "txnId": f"TXN-STRUCT-042-0{i + 1}",
                "fromAccountId": from_acc,
                "toAccountId": f"ACC-BANK-{100 + i}",
                "amount": amt,
                "currency": "INR",
                "channel": "NEFT",
                "merchantId": None,
                "country": "IN",
                "timestamp": ts(-360 + i * 90),
                "description": f"Cash deposit #{i + 1}",
                "_amlPattern": "AML-001-STRUCTURING",
                "_injectedAt": ts(),
            }
            for i, amt in enumerate(amounts)
        ]

    elif pattern == "circular":
        label = "Circular Fund Rotation (3-hop)"
        events = [
            {"txnId": "TXN-CIRC-001", "fromAccountId": "ACC-CIRC-A", "toAccountId": "ACC-CIRC-B", "amount": 500000, "currency": "INR", "channel": "RTGS", "country": "IN", "timestamp": ts(-2880), "_amlPattern": "AML-002-CIRCULAR", "_injectedAt": ts()},
            {"txnId": "TXN-CIRC-002", "fromAccountId": "ACC-CIRC-B", "toAccountId": "ACC-CIRC-C", "amount": 490000, "currency": "INR", "channel": "RTGS", "country": "IN", "timestamp": ts(-1440), "_amlPattern": "AML-002-CIRCULAR", "_injectedAt": ts()},
            {"txnId": "TXN-CIRC-003", "fromAccountId": "ACC-CIRC-C", "toAccountId": "ACC-CIRC-A", "amount": 480000, "currency": "INR", "channel": "RTGS", "country": "IN", "timestamp": ts(-60),   "_amlPattern": "AML-002-CIRCULAR", "_injectedAt": ts()},
        ]

    elif pattern == "fanout":
        label = "Fan-Out Layering (1→10)"
        events = [
            {
                "txnId": f"TXN-FAN-{str(i + 1).zfill(3)}",
                "fromAccountId": "ACC-FAN-SOURCE",
                "toAccountId": f"ACC-FAN-LAYER1-{str(i + 1).zfill(3)}",
                "amount": 100000,
                "currency": "INR",
                "channel": "IMPS",
                "country": "IN",
                "timestamp": ts(-120 + i * 5),
                "description": f"Layer-1 distribution #{i + 1}",
                "_amlPattern": "AML-FANOUT-LAYER1",
                "_injectedAt": ts(),
            }
            for i in range(10)
        ]

    elif pattern == "velocity":
        label = "Velocity Spike (20 txns / 30 min)"
        events = [
            {
                "txnId": f"TXN-VEL-{str(i + 1).zfill(3)}",
                "fromAccountId": "ACC-VEL-007",
                "toAccountId": f"ACC-RND-{1000 + i}",
                "amount": random.randint(10000, 60000),
                "currency": "INR",
                "channel": "UPI",
                "country": "IN",
                "timestamp": ts(-30 + i * 1.5),
                "_amlPattern": "AML-004-VELOCITY",
                "_injectedAt": ts(),
            }
            for i in range(20)
        ]

    elif pattern == "chitfund":
        label = "Chit Fund Aggregation (5 → 1)"
        events = [
            {
                "txnId": f"TXN-CF-{str(i + 1).zfill(3)}",
                "fromAccountId": f"ACC-CF-MEMBER-{i + 1}",
                "toAccountId": "ACC-CF-CHITFUND-01",
                "merchantId": "MERCH-CHITFUND-01",
                "amount": 99000,
                "currency": "INR",
                "channel": "NEFT",
                "country": "IN",
                "timestamp": ts(-i * 20),
                "description": "Chit fund monthly deposit",
                "_amlPattern": "AML-CHITFUND-AGG",
                "_injectedAt": ts(),
            }
            for i in range(5)
        ]

    else:
        return err("Unknown pattern. Valid: structuring | circular | fanout | velocity | chitfund", 400)

    result = await send_events(events, "TRANSACTION")
    for event in events:
        await write_to_fabric(event, "TRANSACTION")

    return ok({
        "success": True,
        "pattern": pattern,
        "label": label,
        "eventsSeeded": len(events),
        "eventIds": [e["txnId"] for e in events],
        **result,
    })


# ── GET / ─────────────────────────────────────────────────────
@app.route(route="", methods=["GET"])
async def serve_root(req: func.HttpRequest) -> func.HttpResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return err("index.html not found", 404)
    return func.HttpResponse(
        body=index.read_bytes(),
        status_code=200,
        mimetype="text/html",
        headers=CORS,
    )


# ── GET /{filepath} ───────────────────────────────────────────
@app.route(route="{*filepath}", methods=["GET"])
async def serve_static(req: func.HttpRequest) -> func.HttpResponse:
    filepath = req.route_params.get("filepath", "")

    # Never serve API paths through static handler
    if filepath.startswith("api/"):
        return err("Not found", 404)

    # Path traversal guard
    target = (STATIC_DIR / filepath).resolve()
    if not str(target).startswith(str(STATIC_DIR.resolve())):
        return err("Forbidden", 403)

    if target.exists() and target.is_file():
        ext = target.suffix.lower()
        mime_map = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        return func.HttpResponse(
            body=target.read_bytes(),
            status_code=200,
            mimetype=mime_map.get(ext, "application/octet-stream"),
            headers=CORS,
        )

    # SPA fallback
    index = STATIC_DIR / "index.html"
    return func.HttpResponse(
        body=index.read_bytes(),
        status_code=200,
        mimetype="text/html",
        headers=CORS,
    )
