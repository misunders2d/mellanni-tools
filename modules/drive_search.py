"""Company Drive search: the mellanni_drive_search tool on the Mellanni MCP server, called with the
user's own MCP sign-in (login.mcp_token). The MCP server checks role and Drive access."""

import asyncio
import json
import re

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from login import MCP_RESOURCE

KINDS = ["image", "screenshot", "video", "audio", "pdf", "doc"]
_FILE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class SearchError(Exception):
    pass


def md_escape(text: str) -> str:
    """Text from Drive (names, excerpts) rendered literally in Streamlit markdown."""
    return "".join("\\" + c if c in "\\[]()*_`$~!<>#|:{}+-=." else c for c in text)


def safe_link(url: str | None) -> str | None:
    """Only Google Drive/Docs links are rendered as links."""
    ok = isinstance(url, str) and url.startswith(("https://drive.google.com/", "https://docs.google.com/"))
    return url if ok else None


def safe_id(file_id: str) -> str | None:
    return file_id if isinstance(file_id, str) and _FILE_ID.match(file_id) else None


async def _call(token: str, args: dict) -> dict:
    async with streamablehttp_client(
        MCP_RESOURCE, headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("mellanni_drive_search", args)
    text = " ".join(getattr(c, "text", "") for c in result.content).strip()
    if result.isError:
        raise SearchError(text or "Drive search failed.")
    if isinstance(result.structuredContent, dict) and "results" in result.structuredContent:
        return result.structuredContent
    return json.loads(text)


def search(token: str, query: str, limit: int, kinds: list[str] | None) -> dict:
    try:
        return asyncio.run(_call(token, {"query": query, "limit": limit, "kinds": kinds or None}))
    except SearchError:
        raise
    except Exception:
        raise SearchError("Mellanni MCP is unavailable or your MCP session expired. Reconnect and try again.") from None
