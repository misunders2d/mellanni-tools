"""Thin wrapper around the DataDive v1 API (https://api.datadive.tools).

All endpoints from the official spec are exposed as functions. GETs are cached
via st.cache_data; POSTs and DELETEs are not.
"""

from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

BASE_URL = "https://api.datadive.tools"
DEFAULT_TIMEOUT = 60.0


def _headers() -> dict[str, str]:
    api_key = st.secrets.get("DATADIVE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DATADIVE_API_KEY missing from st.secrets — add it to .streamlit/secrets.toml"
        )
    return {"accept": "application/json", "x-api-key": api_key}


def _get(path: str, params: dict[str, Any] | None = None) -> dict | list:
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.get(f"{BASE_URL}{path}", params=params, headers=_headers())
        resp.raise_for_status()
        return resp.json()


def _post(path: str, body: dict[str, Any] | None = None) -> dict | list:
    headers = _headers() | {"content-type": "application/json"}
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(f"{BASE_URL}{path}", json=body or {}, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _delete(path: str) -> dict | list:
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.delete(f"{BASE_URL}{path}", headers=_headers())
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return {"status": resp.status_code}


# ---------------------------------------------------------------------------
# Niches
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300, show_spinner=False)
def list_niches(current_page: int = 1, page_size: int = 50) -> dict:
    return _get(
        "/v1/niches", params={"currentPage": current_page, "pageSize": page_size}
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_niche_keywords(niche_id: str) -> dict:
    return _get(f"/v1/niches/{niche_id}/keywords")


@st.cache_data(ttl=300, show_spinner=False)
def get_niche_competitors(niche_id: str) -> dict:
    return _get(f"/v1/niches/{niche_id}/competitors")


@st.cache_data(ttl=300, show_spinner=False)
def get_niche_ranking_juices(niche_id: str) -> dict:
    return _get(f"/v1/niches/{niche_id}/ranking-juices")


@st.cache_data(ttl=300, show_spinner=False)
def get_niche_roots(niche_id: str) -> dict:
    return _get(f"/v1/niches/{niche_id}/roots")


def ai_copywriter(niche_id: str, prompt: str, listing_to_include: dict) -> dict:
    return _post(
        f"/v1/niches/{niche_id}/ai-copywriter",
        body={"prompt": prompt, "listingToInclude": listing_to_include},
    )


def delete_niche(niche_id: str) -> dict:
    return _delete(f"/v1/niches/{niche_id}")


# ---------------------------------------------------------------------------
# Rank Radars
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300, show_spinner=False)
def list_rank_radars(
    niche_id: str | None = None,
    status: str | None = None,
    search_text: str | None = None,
    current_page: int = 1,
    page_size: int = 50,
) -> dict:
    params = {"currentPage": current_page, "pageSize": page_size}
    if niche_id:
        params["nicheId"] = niche_id
    if status:
        params["status"] = status
    if search_text:
        params["searchText"] = search_text
    return _get("/v1/niches/rank-radars", params=params)


@st.cache_data(ttl=300, show_spinner=False)
def get_rank_radar(rank_radar_id: str, start_date: str, end_date: str) -> dict:
    return _get(
        f"/v1/niches/rank-radars/{rank_radar_id}",
        params={"startDate": start_date, "endDate": end_date},
    )


def create_rank_radar(asin: str, number_of_keywords: int, niche_id: str) -> dict:
    return _post(
        "/v1/niches/rank-radars",
        body={
            "asin": asin,
            "numberOfKeywords": number_of_keywords,
            "nicheId": niche_id,
        },
    )


def delete_rank_radar(rank_radar_id: str) -> dict:
    return _delete(f"/v1/niches/rank-radars/{rank_radar_id}")


# ---------------------------------------------------------------------------
# Dives
# ---------------------------------------------------------------------------


def create_niche_dive(marketplace: str, asin: str, number_of_competitors: int) -> dict:
    return _post(
        "/v1/niches/dives",
        body={
            "marketplace": marketplace,
            "asin": asin,
            "numberOfCompetitors": number_of_competitors,
        },
    )


@st.cache_data(ttl=60, show_spinner=False)
def get_niche_dive(dive_id: str) -> dict:
    return _get(f"/v1/niches/dives/{dive_id}")
