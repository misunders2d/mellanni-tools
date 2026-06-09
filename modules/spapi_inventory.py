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
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_POLL_SECONDS = 10
SP_TIMEOUT_MESSAGE = (
    "Amazon inventory report is still being generated. Using BigQuery inventory for this run; "
    "retry in a few minutes for fresher SP-API data."
)


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


def _parse_amazon_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _payload_reports(response: Any) -> list[dict[str, Any]]:
    payload = getattr(response, "payload", response) or {}
    reports = payload.get("reports", []) if isinstance(payload, dict) else []
    return [report for report in reports if isinstance(report, dict)]


def _report_type_matches(value: Any) -> bool:
    text = str(value or "")
    return text == REPORT_TYPE_NAME or text.endswith(REPORT_TYPE_NAME)


def _latest_completed_same_day_report(
    report_client: Reports,
    now_utc: datetime | None = None,
    marketplace_id: str = MARKETPLACE_ID_US,
) -> dict[str, Any] | None:
    """Return newest DONE MYI report created today (UTC), if Amazon already has one."""
    now_utc = now_utc or datetime.now(timezone.utc)
    day_start = now_utc.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    reports: list[dict[str, Any]] = []

    try:
        response = report_client.get_reports(
            reportTypes=[REPORT_TYPE],
            processingStatuses=["DONE"],
            marketplaceIds=[marketplace_id],
            createdSince=day_start.isoformat().replace("+00:00", "Z"),
            pageSize=20,
        )
        reports = _payload_reports(response)
    except Exception:
        response = report_client.get_reports(reportTypes=[REPORT_TYPE], processingStatuses=["DONE"], pageSize=20)
        reports = _payload_reports(response)

    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for report in reports:
        if not _report_type_matches(report.get("reportType")):
            continue
        if report.get("processingStatus") != "DONE":
            continue
        created_at = _parse_amazon_datetime(report.get("createdTime") or report.get("processingEndTime"))
        if created_at is None or created_at.astimezone(timezone.utc) < day_start:
            continue
        candidates.append((created_at, report))

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _create_inventory_report(report_client: Reports, marketplace_id: str) -> str:
    created = report_client.create_report(reportType=REPORT_TYPE, marketplaceIds=[marketplace_id])
    report_id = created.payload.get("reportId")
    if not report_id:
        raise RuntimeError("SP-API inventory report create returned no report id")
    return str(report_id)


def _wait_for_report_done(
    report_client: Reports,
    report_id: str,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    max_wait_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    deadline = time.monotonic() + max_wait_seconds
    status: dict[str, Any] = {}

    while True:
        status = report_client.get_report(reportId=report_id).payload
        processing_status = status.get("processingStatus")
        if processing_status == "DONE":
            return status
        if processing_status in {"CANCELLED", "FATAL"}:
            raise RuntimeError(f"SP-API inventory report {report_id} {processing_status}")
        if time.monotonic() >= deadline:
            raise TimeoutError(SP_TIMEOUT_MESSAGE)
        time.sleep(poll_seconds)


def _download_report_dataframe(report_client: Reports, report_document_id: str) -> pd.DataFrame:
    document = report_client.get_report_document(
        reportDocumentId=report_document_id,
        download=True,
    ).payload.get("document", "")
    return parse_inventory_report_text(document)


def request_inventory_report(
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    max_wait_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    marketplace_id: str = MARKETPLACE_ID_US,
    force_fresh: bool = False,
) -> InventoryReportResult:
    """Reuse today's completed MYI report unless force_fresh requests a new bounded report."""
    report_client = Reports(credentials=get_spapi_credentials())
    reusable = _latest_completed_same_day_report(report_client, marketplace_id=marketplace_id)

    if reusable and not force_fresh:
        status = reusable
        report_id = str(status.get("reportId") or "") or None
    else:
        try:
            report_id = _create_inventory_report(report_client, marketplace_id)
            status = _wait_for_report_done(
                report_client,
                report_id,
                poll_seconds=poll_seconds,
                max_wait_seconds=max_wait_seconds,
            )
        except TimeoutError:
            if reusable:
                status = reusable
                report_id = str(status.get("reportId") or "") or None
            else:
                raise

    document_id = status.get("reportDocumentId")
    if not document_id and report_id:
        status = report_client.get_report(reportId=report_id).payload
        document_id = status.get("reportDocumentId")
    if not document_id:
        raise RuntimeError("SP-API inventory report missing document id")

    return InventoryReportResult(
        data=_download_report_dataframe(report_client, str(document_id)),
        report_id=report_id,
        generated_at=datetime.now(timezone.utc),
    )


def seconds_until_tomorrow(now: datetime | None = None) -> int:
    now = now or datetime.now()
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=now.tzinfo)
    return max(int((midnight - now).total_seconds()), 60)
