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


def parse_response(rpc_response: dict) -> dict:
    """Parse an A2A JSON-RPC response into structured parts.

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
            elif "inlineData" in part:
                inline = part["inlineData"]
                mime = inline.get("mimeType", "")
                import base64

                try:
                    data = base64.b64decode(inline["data"])
                except Exception:
                    data = inline["data"]

                if "image" in mime:
                    result["images"].append(data)
                elif "html" in mime:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    result["html"].append(data)
                elif "csv" in mime:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    result["tables"].append(data)

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
