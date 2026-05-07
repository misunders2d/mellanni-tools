"""A2A (Agent-to-Agent) JSON-RPC client for communicating with remote agents."""

import base64
import logging
import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import streamlit as st

from modules.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


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
    task_id: str | None = None,
) -> dict:
    """Send a JSON-RPC message/send request to a remote A2A agent.

    context_id groups messages into a single session on the remote agent.
    task_id is only for continuing an A2A task that returned input_required.
    Returns the full JSON-RPC response dict.
    """
    payload = build_message_send_payload(message, context_id=context_id, task_id=task_id)

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, json=payload, headers=_build_headers(api_key))
        resp.raise_for_status()
        return resp.json()


def build_message_send_payload(
    message: str,
    context_id: str | None = None,
    task_id: str | None = None,
) -> dict:
    message_obj = {
        "messageId": str(uuid.uuid4()),
        "role": "user",
        "parts": [{"text": message}],
    }
    # context_id maps to session_id on the ADK side, keeping conversation continuity
    if context_id:
        message_obj["contextId"] = context_id
    if task_id:
        message_obj["taskId"] = task_id

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message_obj},
    }
    return payload


def _get_field(data: dict, *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return None


def _guess_mime(name: str | None, fallback: str = "application/octet-stream") -> str:
    if not name:
        return fallback
    guessed, _ = mimetypes.guess_type(name)
    return guessed or fallback


def _add_file(
    result: dict,
    *,
    data: bytes,
    mime: str | None = None,
    name: str | None = None,
    uri: str | None = None,
) -> None:
    mime = mime or _guess_mime(name or uri)
    name = name or Path(urlparse(uri or "").path).name or "artifact"
    result["files"].append({"name": name, "mime_type": mime, "data": data})
    _route_blob(mime, data, result)


def _route_blob(mime: str, data: bytes, result: dict) -> None:
    """Route decoded binary data into the right result bucket by mime type."""
    if "image" in mime:
        result["images"].append(data)
    elif "html" in mime:
        result["html"].append(data.decode("utf-8", errors="replace"))
    elif "csv" in mime:
        result["tables"].append(data.decode("utf-8", errors="replace"))


def _resolve_uri(uri: str, base_url: str | None = None) -> str | None:
    parsed = urlparse(uri)
    if parsed.scheme in {"http", "https"}:
        return uri
    if not parsed.scheme and base_url:
        return urljoin(base_url.rstrip("/") + "/", uri)
    return None


def _fetch_uri(uri: str, api_key: str | None, base_url: str | None = None) -> bytes | None:
    """Fetch a FileWithUri target. Returns None on failure."""
    resolved_uri = _resolve_uri(uri, base_url)
    if not resolved_uri:
        logger.warning("Cannot fetch unsupported file uri %s", uri)
        return None

    headers = {"x-a2a-api-key": api_key} if api_key else {}
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(resolved_uri, headers=headers)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning("Failed to fetch file uri %s: %s", resolved_uri, e)
        return None


def _normalize_part(part: Any) -> dict:
    if not isinstance(part, dict):
        return {}
    root = part.get("root")
    if isinstance(root, dict):
        return root
    return part


def _iter_parts_from_message(message: Any):
    if isinstance(message, dict):
        for part in message.get("parts", []) or []:
            yield _normalize_part(part)


def _iter_task_parts(task: dict):
    status = task.get("status", {})
    if isinstance(status, dict):
        yield from _iter_parts_from_message(status.get("message"))

    if isinstance(task.get("messages"), list):
        for message in task["messages"]:
            yield from _iter_parts_from_message(message)

    for artifact in task.get("artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        for part in artifact.get("parts", []) or []:
            yield _normalize_part(part)


def _decode_blob(raw: Any) -> bytes | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        return base64.b64decode(raw, validate=True)
    except Exception:
        return raw.encode("utf-8")


def _is_allowed_local_artifact(path: str) -> bool:
    resolved = os.path.abspath(path)
    parts = Path(resolved).parts
    allowed_pairs = {("tmp", "plots"), ("tmp", "exports")}
    return any((parts[i], parts[i + 1]) in allowed_pairs for i in range(len(parts) - 1))


def _add_local_file_reference(result: dict, file_path: str, filename: str | None = None) -> None:
    if not _is_allowed_local_artifact(file_path):
        logger.warning("Ignoring local file outside allowed artifact dirs: %s", file_path)
        return
    if not os.path.isfile(file_path):
        logger.warning("Referenced local artifact does not exist: %s", file_path)
        return

    name = filename or os.path.basename(file_path)
    mime = _guess_mime(name or file_path)
    try:
        with open(file_path, "rb") as f:
            _add_file(result, data=f.read(), mime=mime, name=name)
    except Exception as e:
        logger.warning("Failed to read local artifact %s: %s", file_path, e)


def _iter_file_refs(value: Any):
    if isinstance(value, dict):
        file_path = value.get("file_path") or value.get("path")
        if isinstance(file_path, str):
            yield file_path, value.get("filename") or value.get("name"), value.get("data_base64"), value.get("mime_type")

        for nested in value.values():
            if isinstance(nested, (dict, list)):
                yield from _iter_file_refs(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_file_refs(item)


def _remove_markdown_images_when_files_attached(text: str, files: list[dict]) -> str:
    if not text or not files:
        return text
    return _MARKDOWN_IMAGE_RE.sub("", text).strip()


def parse_response(
    rpc_response: dict,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
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
            "files": list[dict],    # Downloadable/renderable files
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
        "files": [],
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

    if isinstance(task, dict) and "parts" in task:
        part_sources = [_normalize_part(part) for part in task.get("parts", [])]
    else:
        part_sources = list(_iter_task_parts(task))

    for part in part_sources:
        if "text" in part:
            result["text"] += str(part["text"])
            continue

        inline = _get_field(part, "inlineData", "inline_data")
        if isinstance(inline, dict):
            mime = _get_field(inline, "mimeType", "mime_type") or ""
            name = _get_field(inline, "displayName", "display_name", "name")
            data = _decode_blob(inline.get("data"))
            if data is not None:
                _add_file(result, data=data, mime=mime, name=name)
            continue

        file_obj = part.get("file")
        if isinstance(file_obj, dict):
            mime = _get_field(file_obj, "mimeType", "mime_type") or ""
            name = file_obj.get("name")
            raw_bytes = file_obj.get("bytes")
            uri = file_obj.get("uri")

            if raw_bytes is not None:
                data = _decode_blob(raw_bytes)
                if data is not None:
                    _add_file(result, data=data, mime=mime, name=name, uri=uri)
                continue

            if uri:
                data = _fetch_uri(uri, api_key, base_url=base_url)
                if data is not None:
                    _add_file(result, data=data, mime=mime, name=name, uri=uri)
                continue

        data_part = part.get("data")
        if data_part is not None:
            for file_path, filename, data_b64, mime in _iter_file_refs(data_part):
                if data_b64:
                    decoded = _decode_blob(data_b64)
                    if decoded:
                        _add_file(result, data=decoded, mime=mime, name=filename)
                    continue
                _add_local_file_reference(result, file_path, filename)

    result["text"] = _remove_markdown_images_when_files_attached(result["text"], result["files"])
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
