import asyncio
import io
import json
import os
from datetime import datetime, timezone

_ingest_client = None


def _is_configured() -> bool:
    uri = os.getenv("FABRIC_KUSTO_CLUSTER_URI", "")
    return bool(uri) and "YOUR_EVENTHOUSE" not in uri


def _get_client():
    global _ingest_client
    if _ingest_client is not None:
        return _ingest_client
    if not _is_configured():
        return None
    try:
        from azure.identity import DefaultAzureCredential
        from azure.kusto.data import KustoConnectionStringBuilder
        from azure.kusto.ingest import QueuedIngestClient

        cluster_uri = os.getenv("FABRIC_KUSTO_CLUSTER_URI")
        # Fabric ingest URI is the cluster URI prefixed with "ingest-"
        ingest_uri = cluster_uri.replace("https://", "https://ingest-", 1)
        credential = DefaultAzureCredential()
        kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
            ingest_uri, credential
        )
        _ingest_client = QueuedIngestClient(kcsb)
        print(f"[Fabric] Connected ingest client for: {cluster_uri}")
    except Exception as exc:
        print(f"[Fabric] Failed to connect: {exc} — skipping Fabric writes.")
        return None
    return _ingest_client


def _build_ingest_props():
    from azure.kusto.ingest import IngestionProperties
    from azure.kusto.ingest.ingestion_properties import DataFormat

    database = os.getenv("FABRIC_DATABASE", "FraudRealtimeDB")
    table = os.getenv("FABRIC_TABLE", "AMLTransactions")
    return IngestionProperties(
        database=database,
        table=table,
        data_format=DataFormat.JSON,
    )


def _ingest_sync(client, row: dict) -> None:
    props = _build_ingest_props()
    stream = io.BytesIO(json.dumps(row, default=str).encode("utf-8"))
    client.ingest_from_stream(stream, ingestion_properties=props)


def _extract_event_id(event: dict) -> str:
    return (
        event.get("txnId")
        or event.get("customerId")
        or event.get("accountId")
        or event.get("merchantId")
        or ""
    )


async def write_to_fabric(event: dict, event_type: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        # Structure matches AMLTransactions table: (EventType, EventId, Payload, IngestedAt)
        row = {
            "EventType": event_type,
            "EventId": _extract_event_id(event),
            "Payload": event,
            "IngestedAt": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(_ingest_sync, client, row)
        print(f"[Fabric] Wrote {event_type} event to AMLTransactions")
    except Exception as exc:
        print(f"[Fabric] Write failed (non-fatal): {exc}")
