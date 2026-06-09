from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import StringIO
import os
import time
from typing import Any

import pandas as pd
import streamlit as st
from sp_api.api import Reports
from sp_api.base import ReportType


REPORT_TYPE = ReportType.GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA
REPORT_TYPE_NAME = "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"
MARKETPLACE_ID_US = "ATVPDKIKX0DER"


@dataclass(frozen=True)
class InventoryReportResult:
    data: pd.DataFrame
    report_id: str | None
    generated_at: datetime


def _secret(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or "")


def get_spapi_credentials() -> dict[str, str]:
    credentials = {
        "refresh_token": _secret("AMZ_REFRESH_TOKEN_US"),
        "lwa_app_id": _secret("AMZ_CLIENT_ID"),
        "lwa_client_secret": _secret("AMZ_CLIENT_SECRET"),
    }
    missing = [key for key, value in credentials.items() if not value]
    if missing:
        raise RuntimeError(f"Missing SP-API credentials: {', '.join(missing)}")
    return credentials


def parse_inventory_report_text(document: str) -> pd.DataFrame:
    """Parse SP-API inventory flat-file document; Amazon reports are usually TSV."""
    if not document:
        return pd.DataFrame()
    first = pd.read_csv(StringIO(document), sep="\t")
    if len(first.columns) == 1 and "," in str(first.columns[0]):
        return pd.read_csv(StringIO(document))
    return first


def request_inventory_report(
    poll_seconds: int = 5,
    max_wait_seconds: int = 90,
    marketplace_id: str = MARKETPLACE_ID_US,
) -> InventoryReportResult:
    """Create, poll, download, and parse one MYI unsuppressed inventory report."""
    report_client = Reports(credentials=get_spapi_credentials())
    created = report_client.create_report(
        reportType=REPORT_TYPE,
        marketplaceIds=[marketplace_id],
    )
    report_id = created.payload["reportId"]
    deadline = time.monotonic() + max_wait_seconds
    status: dict[str, Any] = {}

    while True:
        status = report_client.get_report(reportId=report_id).payload
        processing_status = status.get("processingStatus")
        if processing_status == "DONE":
            break
        if processing_status in {"CANCELLED", "FATAL"}:
            raise RuntimeError(f"SP-API inventory report {processing_status}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"SP-API inventory report still {processing_status or 'pending'}")
        time.sleep(poll_seconds)

    document_id = status.get("reportDocumentId")
    if not document_id:
        raise RuntimeError("SP-API inventory report missing document id")
    document = report_client.get_report_document(reportDocumentId=document_id, download=True).payload.get("document", "")
    return InventoryReportResult(
        data=parse_inventory_report_text(document),
        report_id=report_id,
        generated_at=datetime.now(timezone.utc),
    )


def seconds_until_tomorrow(now: datetime | None = None) -> int:
    now = now or datetime.now()
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=now.tzinfo)
    return max(int((midnight - now).total_seconds()), 60)
