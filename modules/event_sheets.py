from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build


EVENT_SPREADSHEET_ID = "1_gSk2xSDuyEQ9qzI15NJBxVCBZSJMuTKS1pDsvnfes8"
EVENT_CALENDAR_TAB = "event_calendar"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def _service_account_info() -> dict[str, Any]:
    if os.environ.get("GCP_SERVICE_ACCOUNT_JSON"):
        import json

        return json.loads(os.environ["GCP_SERVICE_ACCOUNT_JSON"])
    try:
        return dict(st.secrets["gcp_service_account"])
    except Exception as exc:
        raise RuntimeError("Missing Google service account for Sheets") from exc


def _sheets_service():
    creds = service_account.Credentials.from_service_account_info(
        _service_account_info(),
        scopes=[SHEETS_SCOPE],
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _values_to_dataframe(values: list[list[Any]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()
    header = [str(v).strip() for v in values[0]]
    width = len(header)
    rows = [(row + [""] * width)[:width] for row in values[1:]]
    return pd.DataFrame(rows, columns=header)


def read_sheet_range(spreadsheet_id: str, range_name: str) -> pd.DataFrame:
    service = _sheets_service()
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    return _values_to_dataframe(result.get("values", []))


def read_event_calendar() -> pd.DataFrame:
    return read_sheet_range(EVENT_SPREADSHEET_ID, f"'{EVENT_CALENDAR_TAB}'!A:Z")


def read_event_performance() -> pd.DataFrame:
    """Read first non-calendar tab from the Event performance spreadsheet."""
    service = _sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=EVENT_SPREADSHEET_ID).execute()
    sheets = meta.get("sheets", [])
    titles = [sheet.get("properties", {}).get("title", "") for sheet in sheets]
    performance_title = next((title for title in titles if title and title != EVENT_CALENDAR_TAB), "")
    if not performance_title:
        return pd.DataFrame()
    result = service.spreadsheets().values().get(
        spreadsheetId=EVENT_SPREADSHEET_ID,
        range=f"'{performance_title}'!A:ZZ",
    ).execute()
    return _values_to_dataframe(result.get("values", []))
