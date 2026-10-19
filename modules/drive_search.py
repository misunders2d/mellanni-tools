"""Company Drive search through the Mellanni MCP server, with the signed-in user's own Google token.

The MCP server checks the user's role and Drive access; this module only calls it and fetches previews.
"""

import requests
import streamlit as st

MCP_URL = st.secrets.get("mellanni_mcp_url", "https://mcp.bezosapp.uk")
KINDS = ["image", "screenshot", "video", "audio", "pdf", "doc"]
THUMB_PX = 400

ERRORS = {
    "missing_token": "Google sign-in has no Drive access token. Log out and log in again.",
    "google_token_invalid": "Google session expired. Log out and log in again.",
    "drive_scope_missing": "Drive access was not granted at sign-in. Log out and log in again, and allow Drive access.",
    "not_allowed": "Drive search is not enabled for your account. Contact Sergey.",
}


def md_escape(text: str) -> str:
    """A file name safe inside a markdown link label."""
    return "".join("\\" + c if c in "[]()*_`$~" else c for c in text)


class SearchError(Exception):
    pass


def user_token() -> str | None:
    try:
        return st.user.tokens.get("access")
    except Exception:
        return None


def search(token: str, query: str, limit: int, kinds: list[str] | None) -> dict:
    try:
        response = requests.post(
            f"{MCP_URL}/api/drive-search",
            json={"query": query, "limit": limit, "kinds": kinds or None},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
    except requests.RequestException:
        raise SearchError("Drive search is unavailable right now. Try again later.") from None
    if response.status_code == 200:
        return response.json()
    try:
        code = response.json().get("error", "")
    except ValueError:
        code = ""
    raise SearchError(ERRORS.get(code) or f"Drive search failed ({response.status_code}: {code or 'error'}).")


def thumbnail(token: str, file_id: str) -> bytes | None:
    """The file's Drive preview image, fetched with the user's own token; None when Drive has none."""
    cache = st.session_state.setdefault("drive_thumbs", {})
    if file_id in cache:
        return cache[file_id]
    data = None
    try:
        meta = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "thumbnailLink", "supportsAllDrives": "true"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        link = meta.json().get("thumbnailLink") if meta.ok else None
        if link:
            link = link.rsplit("=s", 1)[0] + f"=s{THUMB_PX}" if "=s" in link else link
            image = requests.get(link, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            if image.ok and image.headers.get("content-type", "").startswith("image/"):
                data = image.content
    except requests.RequestException:
        data = None
    cache[file_id] = data
    return data
