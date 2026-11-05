"""Bounded MCP client facade over the official Streamable HTTP SDK transport."""

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Literal, Protocol

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, ListToolsResult, ServerCapabilities
from pydantic import BaseModel, ConfigDict, ValidationError

from ai_agent.core.config import Settings
from ai_agent.domain.models import SourceLink

# Read-only MVP names from docs/contracts/mcp/tool-catalog.json. P2 tools excluded.
MVP_TOOLS = frozenset(
    {
        "search_logs",
        "query_prometheus",
        "get_trace",
        "get_service_health",
        "get_container_status",
        "get_container_events",
        "get_recent_deployments",
        "github_search_code",
        "github_get_file",
        "github_get_commit",
        "github_compare_commits",
        "github_get_blame",
        "http_health_check",
        "get_incident_context",
    }
)


class MCPClientError(Exception):
    """MCP transport or protocol failure (distinct from application status=error)."""


class MCPTimeoutError(MCPClientError):
    """Connecting, discovery or a tool call exceeded its deadline."""


class MCPToolError(MCPClientError):
    """The server returned native MCP isError for a tool call."""


class MCPProtocolError(MCPClientError):
    """The server response is missing or does not match the draft result shape."""


class ToolErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ToolResult(BaseModel):
    """Application result inside MCP content; not the native MCP envelope."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "empty", "partial", "error"]
    summary: str
    source_refs: list[SourceLink]
    items: list[dict[str, object]]
    truncated: bool
    error: ToolErrorDetail | None = None


class AvailableTool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    input_schema: dict[str, object]
    output_schema: dict[str, object] | None = None


class SessionPort(Protocol):
    @property
    def server_capabilities(self) -> ServerCapabilities: ...

    @property
    def protocol_version(self) -> str: ...

    async def list_tools(self, *, cursor: str | None = None) -> ListToolsResult: ...

    async def call_tool(
        self, name: str, arguments: dict[str, object]
    ) -> CallToolResult: ...


class MCPToolClient:
    """Tool discovery/calls for one already connected SDK session."""

    def __init__(
        self,
        session: SessionPort,
        *,
        call_timeout_seconds: float,
        max_result_bytes: int,
        allowed_tools: frozenset[str] = MVP_TOOLS,
    ) -> None:
        self._session = session
        self._call_timeout = call_timeout_seconds
        self._max_result_bytes = max_result_bytes
        self._allowed = allowed_tools & MVP_TOOLS
        self._discovered: dict[str, AvailableTool] = {}

    @property
    def protocol_version(self) -> str:
        return self._session.protocol_version

    @property
    def server_capabilities(self) -> ServerCapabilities:
        return self._session.server_capabilities

    async def discover(self) -> tuple[AvailableTool, ...]:
        self._discovered = {}
        if self._session.server_capabilities.tools is None:
            raise MCPProtocolError("MCP server does not advertise tools capability")
        found: dict[str, AvailableTool] = {}
        cursor = None
        seen_cursors: set[str] = set()
        try:
            async with asyncio.timeout(self._call_timeout):
                for _ in range(100):
                    page = await self._session.list_tools(cursor=cursor)
                    if not isinstance(page, ListToolsResult):
                        raise MCPProtocolError("Invalid MCP tool list response")
                    if page.result_type != "complete":
                        raise MCPProtocolError("Incomplete MCP tool list")
                    for item in page.tools:
                        if item.name in self._allowed:
                            if item.name in found or not isinstance(
                                item.input_schema, dict
                            ):
                                raise MCPProtocolError("Invalid tool descriptor")
                            found[item.name] = AvailableTool(
                                name=item.name,
                                input_schema=item.input_schema,
                                output_schema=item.output_schema,
                            )
                    cursor = page.next_cursor
                    if cursor is None:
                        self._discovered = found
                        return tuple(found.values())
                    if cursor in seen_cursors:
                        raise MCPProtocolError("Repeated tool-list cursor")
                    seen_cursors.add(cursor)
                raise MCPProtocolError("Tool-list page limit exceeded")
        except TimeoutError as exc:
            raise MCPTimeoutError("MCP discovery timed out") from exc
        except MCPClientError:
            raise
        except Exception as exc:
            raise MCPClientError("MCP discovery failed") from exc

    async def call(self, name: str, arguments: Mapping[str, object]) -> ToolResult:
        if name not in self._discovered:
            raise MCPClientError("Tool was not discovered or is not allowed")
        try:
            async with asyncio.timeout(self._call_timeout):
                response = await self._session.call_tool(name, dict(arguments))
        except TimeoutError as exc:
            raise MCPTimeoutError("MCP tool call timed out") from exc
        except Exception as exc:
            raise MCPClientError("MCP tool call failed") from exc
        if not isinstance(response, CallToolResult):
            raise MCPProtocolError("Invalid MCP tool call response")
        if response.is_error:
            raise MCPToolError("MCP tool returned isError")
        if response.result_type != "complete":
            raise MCPProtocolError("Incomplete MCP tool result")
        payload = response.structured_content
        if payload is None:
            if len(response.content) != 1 or response.content[0].type != "text":
                raise MCPProtocolError("MCP tool returned no single JSON text result")
            raw_text = response.content[0].text
            if len(raw_text.encode("utf-8")) > self._max_result_bytes:
                raise MCPProtocolError("MCP result exceeds size limit")
            try:
                payload = json.loads(raw_text)
            except ValueError as exc:
                raise MCPProtocolError("MCP tool returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise MCPProtocolError("MCP tool result must be an object")
        try:
            payload_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise MCPProtocolError("MCP tool result is not JSON-compatible") from exc
        if payload_size > self._max_result_bytes:
            raise MCPProtocolError("MCP result exceeds size limit")
        try:
            return ToolResult.model_validate(payload, strict=True)
        except ValidationError as exc:
            raise MCPProtocolError("MCP tool result violates draft schema") from exc


@asynccontextmanager
async def connect_mcp(settings: Settings) -> AsyncIterator[MCPToolClient]:
    """Open and close a real SDK Streamable HTTP session."""

    if settings.mcp_url is None:
        raise ValueError("AI_AGENT_MCP_URL is required")
    headers = {}
    if settings.mcp_token is not None:
        headers["Authorization"] = f"Bearer {settings.mcp_token.get_secret_value()}"
    async with AsyncExitStack() as stack:
        try:
            async with asyncio.timeout(settings.mcp_connect_timeout_seconds):
                http_client = await stack.enter_async_context(
                    httpx2.AsyncClient(
                        headers=headers,
                        timeout=httpx2.Timeout(
                            settings.mcp_call_timeout_seconds,
                            connect=settings.mcp_connect_timeout_seconds,
                        ),
                    )
                )
                session = await stack.enter_async_context(
                    Client(
                        streamable_http_client(
                            str(settings.mcp_url), http_client=http_client
                        )
                    )
                )
        except TimeoutError as exc:
            raise MCPTimeoutError("MCP connection timed out") from exc
        except Exception as exc:
            raise MCPClientError("MCP connection failed") from exc
        yield MCPToolClient(
            session,
            call_timeout_seconds=settings.mcp_call_timeout_seconds,
            max_result_bytes=settings.mcp_max_result_bytes,
        )
