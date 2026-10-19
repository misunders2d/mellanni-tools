import base64
import hashlib
import json
import logging
import os
import secrets
import time
from urllib.parse import urlencode

import requests
import streamlit as st
try:  # Streamlit internals used by st.login itself; if a release moves them, MCP sign-in is skipped
    from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
    from streamlit.runtime.scriptrunner_utils.exceptions import StopException
    from streamlit.runtime.scriptrunner_utils.script_run_context import (
        get_script_run_ctx,
    )
except ImportError:
    ForwardMsg = None

    class StopException(Exception):
        pass

from modules.gcloud_modules import pull_dictionary
from modules.supabase_client import get_supabase_client

SUPER_ADMINS = ["2djohar@gmail.com", "sergey@mellanni.com"]

# Mellanni MCP sign-in, chained after the app's Google login (same OAuth flow as Claude
# and other MCP clients). Best effort: if the MCP server is down, login still works.
MCP_URL = "https://mcp.bezosapp.uk"
MCP_RESOURCE = f"{MCP_URL}/mcp"
MCP_SCOPE = "openid https://www.googleapis.com/auth/userinfo.email"
MCP_RETRY_S = 600  # after a failed or abandoned MCP sign-in, don't redirect again for this long
logger = logging.getLogger(__name__)

try:
    bigquery_service_account_info = st.secrets.get("gcp_service_account", "")
except Exception as e:
    print(e)
    bigquery_service_account_info = json.loads(
        os.environ.get("gcp_service_account", "")
    )

pull_dictionary()


def get_current_user() -> dict | None:
    """Look up the logged-in user in Supabase, cached in session state."""
    if "current_user" in st.session_state:
        return st.session_state["current_user"]

    supabase = get_supabase_client()
    result = (
        supabase.table("app_users")
        .select("*")
        .eq("email", st.user.email)
        .eq("is_active", True)
        .execute()
    )

    if result.data:
        st.session_state["current_user"] = result.data[0]
        return result.data[0]

    st.session_state["current_user"] = None
    return None


def login_screen():
    st.header("This app requires authorization.")
    st.subheader("Please log in.")
    st.button(
        "Log in with Google",
        on_click=st.login,
        use_container_width=True,
        type="primary",
    )


@st.cache_resource
def _mcp_state() -> dict:
    """Process-wide: pending sign-ins by state, tokens and last attempt by email."""
    return {"pending": {}, "tokens": {}, "tried": {}}


def _mcp_redirect_uri() -> str:
    return st.secrets["auth"]["redirect_uri"].removesuffix("oauth2callback")


@st.cache_resource(show_spinner=False)
def _mcp_client_id(redirect_uri: str) -> str:
    """Registers this app with the MCP server once per process (dynamic client registration)."""
    response = requests.post(
        f"{MCP_URL}/register",
        json={
            "client_name": "Mellanni Tools",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": MCP_SCOPE,
        },
        timeout=5,
    )
    response.raise_for_status()
    return response.json()["client_id"]


def _mcp_save_tokens(email: str, payload: dict) -> None:
    tokens = _mcp_state()["tokens"]
    old = tokens.get(email, {})
    tokens[email] = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token") or old.get("refresh_token"),
        "expires_at": time.time() + int(payload.get("expires_in", 3600)) - 60,
    }


def _mcp_finish_sign_in(email: str) -> None:
    """Handles the MCP server's redirect back to the app (?code=...&state=...)."""
    params = st.query_params
    pending = _mcp_state()["pending"].pop(params.get("state", ""), None)
    if pending is None:
        st.query_params.clear()
        return
    try:
        if params.get("code") and pending["email"] == email:
            redirect_uri = _mcp_redirect_uri()
            response = requests.post(
                f"{MCP_URL}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": params["code"],
                    "redirect_uri": redirect_uri,
                    "client_id": _mcp_client_id(redirect_uri),
                    "code_verifier": pending["verifier"],
                    "resource": MCP_RESOURCE,
                },
                timeout=10,
            )
            response.raise_for_status()
            _mcp_save_tokens(email, response.json())
    except Exception as e:
        logger.warning("Mellanni MCP sign-in failed: %s", type(e).__name__)
    finally:
        st.query_params.clear()


def _mcp_start_sign_in(email: str) -> None:
    """Sends the browser to the MCP server's Google sign-in, as st.login does."""
    redirect_uri = _mcp_redirect_uri()
    client_id = _mcp_client_id(redirect_uri)
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    pending = _mcp_state()["pending"]
    for key, item in list(pending.items()):
        if time.time() - item["at"] > MCP_RETRY_S:
            pending.pop(key, None)
    pending[state] = {"email": email, "verifier": verifier, "at": time.time()}
    url = f"{MCP_URL}/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": MCP_SCOPE,
            "resource": MCP_RESOURCE,
        }
    )
    ctx = get_script_run_ctx()
    if ctx is not None:
        msg = ForwardMsg()
        msg.auth_redirect.url = url
        ctx.enqueue(msg)
        st.stop()


def mcp_sign_in(force: bool = False) -> None:
    """Signs the user in to the Mellanni MCP server once after the app's Google login.
    Never blocks the app: any failure leaves the user logged in without MCP tools."""
    email = (st.user.email or "").lower()
    if ForwardMsg is None or not email.endswith("@mellanni.com"):
        return
    try:
        if "state" in st.query_params:
            _mcp_finish_sign_in(email)
        state = _mcp_state()
        if force:
            state["tokens"].pop(email, None)
        if email in state["tokens"]:
            return
        if not force and time.time() - state["tried"].get(email, 0) < MCP_RETRY_S:
            return
        state["tried"][email] = time.time()
        _mcp_start_sign_in(email)
    except StopException:
        raise
    except Exception as e:
        logger.warning("Mellanni MCP sign-in skipped: %s", type(e).__name__)


def mcp_token() -> str | None:
    """The user's Mellanni MCP access token, refreshed when needed; None when not signed in."""
    email = (st.user.email or "").lower()
    tokens = _mcp_state()["tokens"]
    entry = tokens.get(email)
    if entry is None:
        return None
    if time.time() < entry["expires_at"]:
        return entry["access_token"]
    try:
        redirect_uri = _mcp_redirect_uri()
        response = requests.post(
            f"{MCP_URL}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": entry["refresh_token"],
                "client_id": _mcp_client_id(redirect_uri),
                "resource": MCP_RESOURCE,
            },
            timeout=10,
        )
        response.raise_for_status()
        _mcp_save_tokens(email, response.json())
        return tokens[email]["access_token"]
    except Exception as e:
        logger.warning("Mellanni MCP token refresh failed: %s", type(e).__name__)
        tokens.pop(email, None)
        return None


def require_login():
    """
    Checks if the user is logged in and authorized via Supabase.
    """
    if not st.user.is_logged_in:
        login_screen()
        st.stop()

    # Hide admin page from sidebar for non-super-admins
    if st.user.email not in SUPER_ADMINS:
        st.markdown(
            '<style>[data-testid="stSidebarNav"] li:has(a[href*="User_Management"]) {display: none;}</style>',
            unsafe_allow_html=True,
        )

    user = get_current_user()
    if user is not None:
        mcp_sign_in()
        with st.sidebar:
            user_picture = (
                user.get("picture_url")
                or (st.user.picture if "picture" in st.user and isinstance(st.user.picture, str) else None)
                or "media/user_avatar.jpg"
            )
            st.image(user_picture, width=50)
            user_name = user.get("name") or st.user.get("name", "Unknown User")
            st.subheader(user_name)
            st.button("Log out", on_click=st.logout)
        return

    st.write("You are not authorized to use this app")
    with st.sidebar:
        st.header(st.user.email)
        st.button("Log out", on_click=st.logout)
    st.stop()


def require_role(*roles: str):
    """Check if the current user has any of the specified roles."""
    user = get_current_user()
    if user is not None:
        user_roles = user.get("roles", [])
        if any(r in user_roles for r in roles):
            return

    st.toast(
        f"User {st.user.email} does not have access to this section. "
        "Contact Sergey for details."
    )
    st.stop()
