import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from services.event_hub_service import send_events
from validators.schemas import (
    AccountEvent,
    BatchRequest,
    CustomerEvent,
    MerchantEvent,
    TransactionEvent,
)

router = APIRouter()


def _uid(prefix: str) -> str:
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"


def ts(offset_minutes: float = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return dt.isoformat()


# ── POST /api/events/transaction ──────────────────────────────
@router.post("/transaction")
async def inject_transaction(body: TransactionEvent):
    event = body.model_dump(exclude_none=False)
    event["txnId"] = event.get("txnId") or _uid("TXN")
    event["timestamp"] = event.get("timestamp") or ts()
    event["_injectedAt"] = ts()
    result = await send_events(event, "TRANSACTION")
    return {"success": True, "eventId": event["txnId"], **result}


# ── POST /api/events/customer ─────────────────────────────────
@router.post("/customer")
async def inject_customer(body: CustomerEvent):
    event = body.model_dump(exclude_none=False)
    event["customerId"] = event.get("customerId") or _uid("CUST")
    event["onboardingDate"] = event.get("onboardingDate") or ts()
    event["_injectedAt"] = ts()
    result = await send_events(event, "CUSTOMER")
    return {"success": True, "eventId": event["customerId"], **result}


# ── POST /api/events/account ──────────────────────────────────
@router.post("/account")
async def inject_account(body: AccountEvent):
    event = body.model_dump(exclude_none=False)
    event["accountId"] = event.get("accountId") or _uid("ACC")
    event["openDate"] = event.get("openDate") or ts()
    event["_injectedAt"] = ts()
    result = await send_events(event, "ACCOUNT")
    return {"success": True, "eventId": event["accountId"], **result}


# ── POST /api/events/merchant ─────────────────────────────────
@router.post("/merchant")
async def inject_merchant(body: MerchantEvent):
    event = body.model_dump(exclude_none=False)
    event["merchantId"] = event.get("merchantId") or _uid("MERCH")
    event["_injectedAt"] = ts()
    result = await send_events(event, "MERCHANT")
    return {"success": True, "eventId": event["merchantId"], **result}


# ── POST /api/events/batch ────────────────────────────────────
@router.post("/batch")
async def inject_batch(body: BatchRequest):
    enriched = [
        {**item.data, "_eventType": item.type, "_injectedAt": ts()}
        for item in body.events
    ]
    result = await send_events(enriched, "BATCH")
    return {"success": True, **result}


# ── POST /api/events/seed/{pattern} ──────────────────────────
@router.post("/seed/{pattern}")
async def seed_pattern(pattern: str):
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
        import random
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
        raise HTTPException(
            status_code=400,
            detail="Unknown pattern. Valid: structuring | circular | fanout | velocity | chitfund",
        )

    result = await send_events(events, "TRANSACTION")
    return {
        "success": True,
        "pattern": pattern,
        "label": label,
        "eventsSeeded": len(events),
        "eventIds": [e["txnId"] for e in events],
        **result,
    }
