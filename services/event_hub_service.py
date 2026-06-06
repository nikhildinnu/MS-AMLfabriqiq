import json
import os
from datetime import datetime, timezone
from typing import Union

_producer = None


def _is_configured() -> bool:
    conn_str = os.getenv("EVENT_HUB_CONNECTION_STRING", "")
    return bool(conn_str) and "YOUR_NAMESPACE" not in conn_str


async def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    if not _is_configured():
        print("[EventHub] No connection string — running in DEMO mode.")
        return None
    try:
        from azure.eventhub.aio import EventHubProducerClient
        conn_str = os.getenv("EVENT_HUB_CONNECTION_STRING")
        hub_name = os.getenv("EVENT_HUB_NAME", "transactions-stream")
        _producer = EventHubProducerClient.from_connection_string(
            conn_str, eventhub_name=hub_name
        )
        print(f"[EventHub] Connected to: {hub_name}")
    except Exception as exc:
        print(f"[EventHub] Failed to connect: {exc} — falling back to DEMO mode.")
        return None
    return _producer


async def send_events(payload: Union[dict, list], event_type: str = "TRANSACTION") -> dict:
    events = payload if isinstance(payload, list) else [payload]
    producer = await _get_producer()

    if producer is None:
        print(f"[DEMO] Would send {len(events)} {event_type} event(s):")
        print(json.dumps(events[0], indent=2, default=str))
        return {"sent": True, "demo": True, "count": len(events)}

    from azure.eventhub import EventData

    batch = await producer.create_batch()
    for event in events:
        envelope = {
            "body": event,
            "properties": {
                "eventType": event_type,
                "source": "aml-event-injector",
                "schemaVersion": "1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        data = EventData(json.dumps(envelope, default=str))
        try:
            batch.add(data)
        except ValueError:
            await producer.send_batch(batch)
            batch = await producer.create_batch()
            batch.add(data)

    await producer.send_batch(batch)
    print(f"[EventHub] Sent {len(events)} {event_type} event(s)")
    return {"sent": True, "demo": False, "count": len(events)}


async def close_producer():
    global _producer
    if _producer is not None:
        await _producer.close()
        _producer = None
