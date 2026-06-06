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
        from azure.kusto.ingest import ManagedStreamingIngestClient

        cluster_uri = os.getenv("FABRIC_KUSTO_CLUSTER_URI")
        credential = DefaultAzureCredential()
        kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
            cluster_uri, credential
        )
        _ingest_client = ManagedStreamingIngestClient.from_connection_string(kcsb)
        print(f"[Fabric] Connected to: {cluster_uri}")
    except Exception as exc:
        print(f"[Fabric] Failed to connect: {exc} — skipping Fabric writes.")
        return None
    return _ingest_client


def _build_ingest_props():
    from azure.kusto.ingest import IngestionProperties
    from azure.kusto.ingest.ingestion_properties import DataFormat

    database = os.getenv("FABRIC_DATABASE", "FraudDetectionDB")
    table = os.getenv("FABRIC_TABLE", "transactions")
    return IngestionProperties(
        database=database,
        table=table,
        data_format=DataFormat.JSON,
    )


def _ingest_sync(client, row: dict) -> None:
    props = _build_ingest_props()
    stream = io.BytesIO(json.dumps(row, default=str).encode("utf-8"))
    client.ingest_from_stream(stream, ingestion_properties=props)


async def write_to_fabric(event: dict, event_type: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        row = {
            **event,
            "EventType": event_type,
            "IngestedAt": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(_ingest_sync, client, row)
        print(f"[Fabric] Wrote {event_type} event to table")
    except Exception as exc:
        print(f"[Fabric] Write failed (non-fatal): {exc}")
