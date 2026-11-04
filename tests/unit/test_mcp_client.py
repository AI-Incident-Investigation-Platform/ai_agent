import asyncio
import json
from pathlib import Path

import pytest
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolsCapability,
)

from ai_agent.core.config import Settings
from ai_agent.mcp.client import (
    MVP_TOOLS,
    MCPClientError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPToolClient,
    MCPToolError,
    connect_mcp,
)

CATALOG = Path(__file__).resolve().parents[2] / "docs/contracts/mcp/tool-catalog.json"
PAYLOAD = {
    "status": "ok",
    "summary": "fake result",
    "source_refs": [],
    "items": [{"message": "fake data"}],
    "truncated": False,
    "error": None,
}


class FakeSession:
    protocol_version = "2026-07-28"

    def __init__(self, *, pages=None, response=None, capability=True):
        self.server_capabilities = ServerCapabilities(
            tools=ToolsCapability() if capability else None
        )
        self.pages = pages or [ListToolsResult(tools=[tool("search_logs")])]
        self.response = response or CallToolResult(
            content=[], structuredContent=PAYLOAD
        )
        self.calls = []

    async def list_tools(self, *, cursor=None):
        self.calls.append(("list", cursor))
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return page

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def tool(name):
    return Tool(name=name, inputSchema={"type": "object", "properties": {}})


def client(session, *, timeout=1, max_bytes=4096):
    return MCPToolClient(
        session, call_timeout_seconds=timeout, max_result_bytes=max_bytes
    )


def test_allowlist_matches_mvp_catalog_and_excludes_p2():
    catalog = json.loads(CATALOG.read_text())
    assert MVP_TOOLS == {
        name for name, spec in catalog["tools"].items() if spec["phase"] == "MVP"
    }


def test_discovery_filters_unknown_tools_and_paginates():
    session = FakeSession(
        pages=[
            ListToolsResult(
                tools=[tool("write_file"), tool("search_logs")], nextCursor="next"
            ),
            ListToolsResult(tools=[tool("query_prometheus")]),
        ]
    )
    facade = client(session)

    async def scenario():
        found = await facade.discover()
        assert [item.name for item in found] == ["search_logs", "query_prometheus"]
        with pytest.raises(MCPClientError, match="not discovered"):
            await facade.call("write_file", {})
        result = await facade.call("search_logs", {"query": "fake"})
        assert result.status == "ok"
        assert result.items == [{"message": "fake data"}]

    asyncio.run(scenario())
    assert session.calls == [
        ("list", None),
        ("list", "next"),
        ("search_logs", {"query": "fake"}),
    ]


def test_missing_tools_capability_is_rejected():
    with pytest.raises(MCPProtocolError, match="capability"):
        asyncio.run(client(FakeSession(capability=False)).discover())


def test_protocol_and_capabilities_are_exposed():
    facade = client(FakeSession())
    assert facade.protocol_version == "2026-07-28"
    assert facade.server_capabilities.tools is not None


def test_repeated_cursor_and_duplicate_descriptor_are_rejected():
    async def scenario(pages):
        await client(FakeSession(pages=pages)).discover()

    with pytest.raises(MCPProtocolError, match="cursor"):
        asyncio.run(scenario([ListToolsResult(tools=[], nextCursor="same")] * 2))
    with pytest.raises(MCPProtocolError, match="descriptor"):
        asyncio.run(scenario([ListToolsResult(tools=[tool("search_logs")] * 2)]))
    with pytest.raises(MCPProtocolError, match="response"):
        asyncio.run(scenario([{"tools": []}]))


@pytest.mark.parametrize("status", ["empty", "partial", "error"])
def test_application_status_is_not_native_mcp_error(status):
    payload = {**PAYLOAD, "status": status}
    facade = client(
        FakeSession(response=CallToolResult(content=[], structuredContent=payload))
    )

    async def scenario():
        await facade.discover()
        assert (await facade.call("search_logs", {})).status == status

    asyncio.run(scenario())


def test_native_is_error_is_distinct_from_application_status():
    session = FakeSession(
        response=CallToolResult(
            content=[TextContent(type="text", text="private server error")],
            isError=True,
        )
    )

    async def scenario():
        facade = client(session)
        await facade.discover()
        with pytest.raises(MCPToolError, match="isError"):
            await facade.call("search_logs", {})

    asyncio.run(scenario())


def test_bad_native_call_response_is_rejected():
    async def scenario():
        facade = client(FakeSession(response={"content": []}))
        await facade.discover()
        await facade.call("search_logs", {})

    with pytest.raises(MCPProtocolError, match="response"):
        asyncio.run(scenario())


def test_single_text_json_fallback_and_invalid_responses():
    async def scenario(response):
        facade = client(FakeSession(response=response))
        await facade.discover()
        return await facade.call("search_logs", {})

    text_response = CallToolResult(
        content=[TextContent(type="text", text=json.dumps(PAYLOAD))]
    )
    assert asyncio.run(scenario(text_response)).status == "ok"
    for response in (
        CallToolResult(content=[TextContent(type="text", text="not JSON")]),
        CallToolResult(content=[]),
        CallToolResult(content=[], structuredContent={"status": "ok"}),
        CallToolResult(
            content=[], structuredContent=PAYLOAD, resultType="input_required"
        ),
    ):
        with pytest.raises(MCPProtocolError):
            asyncio.run(scenario(response))


def test_oversized_response_is_rejected():
    async def scenario():
        facade = client(
            FakeSession(
                response=CallToolResult(
                    content=[], structuredContent={**PAYLOAD, "summary": "x" * 5000}
                )
            )
        )
        await facade.discover()
        await facade.call("search_logs", {})

    with pytest.raises(MCPProtocolError, match="size limit"):
        asyncio.run(scenario())


def test_call_timeout_and_transport_error():
    class SlowSession(FakeSession):
        async def call_tool(self, name, arguments):
            await asyncio.sleep(0.1)
            return self.response

    async def scenario(session, error):
        facade = client(session, timeout=0.01)
        await facade.discover()
        with pytest.raises(error):
            await facade.call("search_logs", {})

    asyncio.run(scenario(SlowSession(), MCPTimeoutError))
    asyncio.run(scenario(FakeSession(response=OSError("secret")), MCPClientError))


def test_cancellation_propagates():
    class SlowSession(FakeSession):
        async def call_tool(self, name, arguments):
            await asyncio.sleep(10)

    async def scenario():
        facade = client(SlowSession())
        await facade.discover()
        task = asyncio.create_task(facade.call("search_logs", {}))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_missing_url_is_configuration_error():
    async def scenario():
        async with connect_mcp(Settings(mcp_url=None)):
            pass

    with pytest.raises(ValueError, match="MCP_URL"):
        asyncio.run(scenario())


def test_connection_failure_is_controlled():
    async def scenario():
        async with connect_mcp(
            Settings(
                mcp_url="http://127.0.0.1:1/mcp",
                mcp_connect_timeout_seconds=0.5,
            )
        ):
            pass

    with pytest.raises(MCPClientError, match="connection failed"):
        asyncio.run(scenario())
