"""A2A (Agent-to-Agent) JSON-RPC client for communicating with remote agents."""

import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import secrets as secrets_mod
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
import streamlit as st
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def get_remote_agent(preferred_name: str | None = None) -> dict | None:
    """Fetch the primary remote agent config from Supabase, cached in session state.

    If preferred_name is provided, pick that active agent first and fall back to
    the first active agent. This lets production move from Ori to the server-side
    ``you`` agent without requiring all older rows to be disabled immediately.
    """
    cache_key = f"remote_agent:{preferred_name or 'default'}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    supabase = get_supabase_client()

    if preferred_name:
        preferred = (
            supabase.table("remote_agents")
            .select("*")
            .eq("is_active", True)
            .eq("name", preferred_name.lower())
            .limit(1)
            .execute()
        )
        if preferred.data:
            st.session_state[cache_key] = preferred.data[0]
            return preferred.data[0]

    result = (
        supabase.table("remote_agents")
        .select("*")
        .eq("is_active", True)
        .order("name")
        .limit(1)
        .execute()
    )

    if result.data:
        st.session_state[cache_key] = result.data[0]
        return result.data[0]

    st.session_state[cache_key] = None
    return None


def clear_cached_remote_agents() -> None:
    """Clear cached remote-agent selections after admin changes."""
    for key in list(st.session_state.keys()):
        if str(key).startswith("remote_agent"):
            del st.session_state[key]


def update_remote_agent_url(agent_name: str, new_url: str):
    """Update a remote agent's URL in Supabase (called when agent broadcasts new address)."""
    supabase = get_supabase_client()
    supabase.table("remote_agents").update(
        {"url": new_url.rstrip("/")}
    ).eq("name", agent_name).execute()

    clear_cached_remote_agents()


def _load_ed25519_private_key(pem: str | bytes) -> Ed25519PrivateKey:
    if isinstance(pem, str):
        pem = pem.encode("utf-8")
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("A2A signing key must be Ed25519")
    return key


def _sign_a2a_headers(
    method: str,
    path: str,
    body: bytes,
    *,
    agent_id: str,
    principal: str,
    key_id: str,
    private_key: Ed25519PrivateKey,
) -> dict:
    timestamp = str(int(time.time()))
    nonce = secrets_mod.token_hex(16)
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(
        [method.upper(), path or "/", agent_id, principal, timestamp, nonce, body_hash]
    ).encode("utf-8")
    signature = private_key.sign(canonical)
    return {
        "X-A2A-Agent-ID": agent_id,
        "X-A2A-Key-ID": key_id,
        "X-A2A-Principal": principal,
        "X-A2A-Timestamp": timestamp,
        "X-A2A-Nonce": nonce,
        "X-A2A-Signature": base64.b64encode(signature).decode("ascii"),
    }


def _build_headers(
    api_key: str | None = None,
    app_token: str | None = None,
    client_id: str | None = None,
    scoped_token: str | None = None,
    signed: dict | None = None,
) -> dict:
    """Build server-to-server auth headers for the remote hub/agent.

    Signed scoped flow (modern): scoped_token Bearer + Ed25519 signed bundle
    only — no legacy api_key / app_token / X-A2A-Client-ID mixed in. Falls
    back to the legacy header set when no signing material is provided.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "mellanni-tools-streamlit-a2a-client",
    }
    if signed:
        if scoped_token:
            headers["Authorization"] = f"Bearer {scoped_token}"
        headers.update(signed)
        return headers
    if scoped_token:
        headers["Authorization"] = f"Bearer {scoped_token}"
    elif app_token:
        headers["Authorization"] = f"Bearer {app_token}"
    if api_key:
        headers["x-a2a-api-key"] = api_key
    if client_id:
        headers["X-A2A-Client-ID"] = client_id
        headers["X-A2A-Agent-ID"] = client_id
    return headers


def _json_rpc_fallback_url(url: str) -> str | None:
    """Return known JSON-RPC alias for hub URLs that 404 at origin root."""
    parsed = urlparse(url)
    if parsed.path.rstrip("/") in {"", "/"}:
        return urlunparse(parsed._replace(path="/a2a/rpc"))
    return None


def _json_rpc_error_message(resp: httpx.Response) -> str | None:
    """Extract JSON-RPC error from non-2xx hub responses before httpx hides it."""
    try:
        body = resp.json()
    except Exception:
        return None
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return None
    message = error.get("message") or str(error)
    code = error.get("code")
    if code is not None:
        return f"JSON-RPC error {code}: {message}"
    return f"JSON-RPC error: {message}"


def _signed_headers_for(
    url: str,
    body: bytes,
    method: str,
    *,
    agent_id: str | None,
    principal: str | None,
    key_id: str | None,
    private_key_pem: str | bytes | None,
) -> dict | None:
    if not (agent_id and principal and key_id and private_key_pem):
        return None
    private_key = _load_ed25519_private_key(private_key_pem)
    path = urlparse(url).path or "/"
    return _sign_a2a_headers(
        method,
        path,
        body,
        agent_id=agent_id,
        principal=principal,
        key_id=key_id,
        private_key=private_key,
    )


async def _post_signed_jsonrpc(
    url: str,
    payload: dict,
    *,
    api_key: str | None = None,
    app_token: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    principal: str | None = None,
    key_id: str | None = None,
    private_key_pem: str | bytes | None = None,
    scoped_token: str | None = None,
    timeout: float = 300.0,
) -> dict:
    body_bytes = json.dumps(payload).encode("utf-8")

    def _build(target: str) -> dict:
        signed = _signed_headers_for(
            target, body_bytes, "POST",
            agent_id=agent_id, principal=principal, key_id=key_id,
            private_key_pem=private_key_pem,
        )
        return _build_headers(
            api_key=api_key, app_token=app_token, client_id=client_id,
            scoped_token=scoped_token, signed=signed,
        )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, content=body_bytes, headers=_build(url))
        if resp.status_code == 404:
            fallback_url = _json_rpc_fallback_url(url)
            if fallback_url and fallback_url != url:
                logger.info("A2A root endpoint returned 404; retrying %s", fallback_url)
                resp = await client.post(fallback_url, content=body_bytes, headers=_build(fallback_url))
        rpc_error = _json_rpc_error_message(resp)
        if rpc_error:
            raise RuntimeError(rpc_error)
        resp.raise_for_status()
        return resp.json()


async def send_message(
    url: str,
    api_key: str | None = None,
    message: str = "",
    context_id: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    app_token: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    principal: str | None = None,
    key_id: str | None = None,
    private_key_pem: str | bytes | None = None,
    scoped_token: str | None = None,
) -> dict:
    """Send a JSON-RPC message/send request to a remote A2A agent.

    context_id groups messages into a single session on the remote agent.
    task_id is only for continuing an A2A task that returned input_required.
    When ``private_key_pem`` + identity params are supplied, every request is
    Ed25519-signed per the hub's scoped-token-plus-signature scheme.
    """
    payload = build_message_send_payload(
        message,
        context_id=context_id,
        task_id=task_id,
        metadata=metadata,
    )
    return await _post_signed_jsonrpc(
        url, payload,
        api_key=api_key, app_token=app_token, client_id=client_id,
        agent_id=agent_id, principal=principal, key_id=key_id,
        private_key_pem=private_key_pem, scoped_token=scoped_token,
    )


async def get_task(
    url: str,
    task_id: str,
    *,
    api_key: str | None = None,
    app_token: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    principal: str | None = None,
    key_id: str | None = None,
    private_key_pem: str | bytes | None = None,
    scoped_token: str | None = None,
) -> dict:
    """Fetch current task state via JSON-RPC ``tasks/get``."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/get",
        "params": {"id": task_id},
    }
    return await _post_signed_jsonrpc(
        url, payload,
        api_key=api_key, app_token=app_token, client_id=client_id,
        agent_id=agent_id, principal=principal, key_id=key_id,
        private_key_pem=private_key_pem, scoped_token=scoped_token,
        timeout=60.0,
    )


def build_message_send_payload(
    message: str,
    context_id: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
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
    if metadata:
        message_obj["metadata"] = metadata

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
    file_key = (name, mime, hashlib.sha256(data).hexdigest())
    if file_key in result["_file_keys"]:
        return
    result["_file_keys"].add(file_key)
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


def _origin_tuple(uri: str) -> tuple[str, str, int | None] | None:
    parsed = urlparse(uri)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.port is not None:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 80
    return parsed.scheme, parsed.hostname.lower(), port


def _is_same_origin(uri: str, base_url: str | None) -> bool:
    if not base_url:
        return False
    return _origin_tuple(uri) == _origin_tuple(base_url)


def _fetch_uri(
    uri: str,
    api_key: str | None = None,
    app_token: str | None = None,
    client_id: str | None = None,
    base_url: str | None = None,
    agent_id: str | None = None,
    principal: str | None = None,
    key_id: str | None = None,
    private_key_pem: str | bytes | None = None,
    scoped_token: str | None = None,
) -> bytes | None:
    """Fetch a FileWithUri target. Returns None on failure."""
    resolved_uri = _resolve_uri(uri, base_url)
    if not resolved_uri:
        logger.warning("Cannot fetch unsupported file uri %s", uri)
        return None

    if not _is_same_origin(resolved_uri, base_url):
        logger.warning("Refusing to fetch external file uri %s", resolved_uri)
        return None

    signed = _signed_headers_for(
        resolved_uri,
        b"",
        "GET",
        agent_id=agent_id,
        principal=principal,
        key_id=key_id,
        private_key_pem=private_key_pem,
    )
    headers = _build_headers(
        api_key=api_key,
        app_token=app_token,
        client_id=client_id,
        scoped_token=scoped_token,
        signed=signed,
    )
    headers.pop("Content-Type", None)
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


def _part_key(part: dict) -> tuple:
    text = part.get("text")
    if text:
        return ("text", text)
    inline = _get_field(part, "inlineData", "inline_data")
    if isinstance(inline, dict):
        return ("inline", inline.get("data", ""))
    file_obj = part.get("file")
    if isinstance(file_obj, dict):
        return ("file", file_obj.get("bytes", ""), file_obj.get("uri", ""))
    return None


def _iter_parts_from_message(message: Any):
    if isinstance(message, dict):
        # Skip user messages to prevent echoing user input back as output.
        # Accept both "model" (ADK native) and "agent" (A2A protocol) roles.
        if message.get("role") == "user":
            return
        parts = message.get("parts") or []
        for part in parts:
            yield _normalize_part(part)
        # Hub fallback shape: bare {"role": "assistant", "content": "..."}
        # with no parts array. Synthesize a text part so the parser surfaces it.
        if not parts:
            content = message.get("content")
            if isinstance(content, str) and content:
                yield {"text": content}


def _iter_task_parts(task: dict):
    _seen = set()

    def _dedup(parts):
        for part in parts:
            key = _part_key(part)
            if key is not None and key in _seen:
                continue
            if key is not None:
                _seen.add(key)
            yield part

    status = task.get("status", {})
    if isinstance(status, dict):
        yield from _dedup(_iter_parts_from_message(status.get("message")))

    if isinstance(task.get("messages"), list):
        for message in task["messages"]:
            yield from _dedup(_iter_parts_from_message(message))

    if isinstance(task.get("history"), list):
        for message in task["history"]:
            yield from _dedup(_iter_parts_from_message(message))

    for artifact in task.get("artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        yield from _dedup(
            _normalize_part(part) for part in (artifact.get("parts", []) or [])
        )


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


_ALLOW_LOCAL_ARTIFACTS = os.environ.get("A2A_ALLOW_LOCAL_ARTIFACT_REFS", "").lower() in (
    "1",
    "true",
    "yes",
)


def _add_local_file_reference(result: dict, file_path: str, filename: str | None = None) -> None:
    """Read a file from the local filesystem and attach it as an artifact.

    Only useful when the A2A server and this client share a filesystem
    (local dev: both on the same machine). For remote peers — including
    Streamlit Cloud and any cross-host deploy — the absolute paths the
    server emits cannot resolve here, so we silently skip and rely on
    the bytes-bearing branches (inline_data / FilePart-with-bytes) to
    deliver the file. Opt back in by setting
    ``A2A_ALLOW_LOCAL_ARTIFACT_REFS=true``.
    """
    if not _ALLOW_LOCAL_ARTIFACTS:
        return
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
    app_token: str | None = None,
    client_id: str | None = None,
    base_url: str | None = None,
    agent_id: str | None = None,
    principal: str | None = None,
    key_id: str | None = None,
    private_key_pem: str | bytes | None = None,
    scoped_token: str | None = None,
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
        "_file_keys": set(),
    }

    if "error" in rpc_response:
        error = rpc_response["error"]
        result["error"] = error.get("message", str(error))
        result["state"] = "failed"
        result.pop("_file_keys", None)
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
                data = _fetch_uri(
                    uri,
                    api_key=api_key,
                    app_token=app_token,
                    client_id=client_id,
                    base_url=base_url,
                    agent_id=agent_id,
                    principal=principal,
                    key_id=key_id,
                    private_key_pem=private_key_pem,
                    scoped_token=scoped_token,
                )
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
    result.pop("_file_keys", None)
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
