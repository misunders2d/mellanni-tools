"""A2A (Agent-to-Agent) JSON-RPC client for communicating with remote agents."""

import uuid
import logging
from typing import AsyncIterator

import httpx
import streamlit as st

from modules.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_remote_agent() -> dict | None:
    """Fetch the primary remote agent config from Supabase, cached in session state."""
    if "remote_agent" in st.session_state:
        return st.session_state["remote_agent"]

    supabase = get_supabase_client()
    result = (
        supabase.table("remote_agents")
        .select("*")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if result.data:
        st.session_state["remote_agent"] = result.data[0]
        return result.data[0]

    st.session_state["remote_agent"] = None
    return None


def update_remote_agent_url(agent_name: str, new_url: str):
    """Update a remote agent's URL in Supabase (called when agent broadcasts new address)."""
    supabase = get_supabase_client()
    supabase.table("remote_agents").update(
        {"url": new_url.rstrip("/")}
    ).eq("name", agent_name).execute()

    # Clear cached value so next call fetches fresh
    if "remote_agent" in st.session_state:
        del st.session_state["remote_agent"]


def _build_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "x-a2a-api-key": api_key,
    }


async def send_message(
    url: str,
    api_key: str,
    message: str,
    context_id: str | None = None,
) -> dict:
    """Send a JSON-RPC message/send request to a remote A2A agent.

    context_id groups messages into a single session on the remote agent.
    Returns the full JSON-RPC response dict.
    """
    message_obj = {
        "messageId": str(uuid.uuid4()),
        "role": "user",
        "parts": [{"text": message}],
    }
    # context_id maps to session_id on the ADK side, keeping conversation continuity
    if context_id:
        message_obj["contextId"] = context_id

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message_obj},
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, json=payload, headers=_build_headers(api_key))
        resp.raise_for_status()
        return resp.json()


def _route_blob(mime: str, data: bytes, result: dict) -> None:
    """Route decoded binary data into the right result bucket by mime type."""
    if "image" in mime:
        result["images"].append(data)
    elif "html" in mime:
        result["html"].append(data.decode("utf-8", errors="replace"))
    elif "csv" in mime:
        result["tables"].append(data.decode("utf-8", errors="replace"))


def _fetch_uri(uri: str, api_key: str | None) -> bytes | None:
    """Fetch a FileWithUri target. Returns None on failure."""
    headers = {"x-a2a-api-key": api_key} if api_key else {}
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(uri, headers=headers)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning("Failed to fetch file uri %s: %s", uri, e)
        return None


def parse_response(rpc_response: dict, api_key: str | None = None) -> dict:
    """Parse an A2A JSON-RPC response into structured parts.

    Handles both Google ADK's `inlineData` parts and the A2A-standard
    `FilePart` shape (`{"file": {"bytes": ..., "mimeType": ...}}` or
    `{"file": {"uri": ..., "mimeType": ...}}`). URI-backed files are
    fetched using the provided api_key.

    Returns:
        {
            "text": str,           # Combined text from all artifacts
            "images": list[bytes], # Decoded image data
            "html": list[str],     # HTML content (plots)
            "tables": list[str],   # CSV text data
            "task_id": str,        # For multi-turn conversations
            "state": str,          # completed, input_required, failed, etc.
            "error": str | None,   # Error message if any
        }
    """
    import base64

    result = {
        "text": "",
        "images": [],
        "html": [],
        "tables": [],
        "task_id": None,
        "state": "unknown",
        "error": None,
    }

    if "error" in rpc_response:
        error = rpc_response["error"]
        result["error"] = error.get("message", str(error))
        result["state"] = "failed"
        return result

    task = rpc_response.get("result", {})
    result["task_id"] = task.get("id")

    status = task.get("status", {})
    result["state"] = status.get("state", "unknown")

    # Extract text from status message (if present)
    status_message = status.get("message", {})
    if isinstance(status_message, dict):
        for part in status_message.get("parts", []):
            if "text" in part:
                result["text"] += part["text"]

    # Extract content from artifacts
    for artifact in task.get("artifacts", []):
        for part in artifact.get("parts", []):
            if "text" in part:
                result["text"] += part["text"]
                continue

            # Google ADK / Gemini-style inline data.
            if "inlineData" in part:
                inline = part["inlineData"]
                mime = inline.get("mimeType", "")
                try:
                    data = base64.b64decode(inline["data"])
                except Exception:
                    raw = inline.get("data", "")
                    data = raw.encode("utf-8") if isinstance(raw, str) else raw
                _route_blob(mime, data, result)
                continue

            # A2A-standard FilePart. ADK's agent_to_a2a converter emits this
            # for any binary content (base64 bytes) or referenced file (uri).
            if "file" in part:
                file_obj = part["file"] or {}
                mime = file_obj.get("mimeType", "")
                if "bytes" in file_obj and file_obj["bytes"] is not None:
                    try:
                        data = base64.b64decode(file_obj["bytes"])
                    except Exception as e:
                        logger.warning("Failed to decode file.bytes: %s", e)
                        continue
                    _route_blob(mime, data, result)
                elif "uri" in file_obj and file_obj["uri"]:
                    data = _fetch_uri(file_obj["uri"], api_key)
                    if data is not None:
                        _route_blob(mime, data, result)

    return result


async def discover_agent(base_url: str) -> dict | None:
    """Fetch a remote agent's card via standard .well-known discovery."""
    base_url = base_url.rstrip("/")
    paths = ["/.well-known/agent-card.json", "/.well-known/agent.json"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for path in paths:
            try:
                resp = await client.get(f"{base_url}{path}")
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
    return None
