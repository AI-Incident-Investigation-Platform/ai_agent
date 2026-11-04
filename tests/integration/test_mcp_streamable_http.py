import asyncio
import socket

import pytest
import uvicorn
from mcp.server.mcpserver import MCPServer

from ai_agent.core.config import Settings
from ai_agent.mcp.client import MCPClientError, connect_mcp


def test_real_sdk_streamable_http_round_trip():
    async def scenario():
        server_impl = MCPServer(name="ai-05-fake-server", version="1")
        called = []

        @server_impl.tool()
        def search_logs(query: str) -> dict:
            called.append(query)
            return {
                "status": "empty",
                "summary": "No fake logs",
                "source_refs": [],
                "items": [],
                "truncated": False,
                "error": None,
            }

        @server_impl.tool()
        def write_file(path: str) -> dict:
            called.append(path)
            return {"status": "ok"}

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        sock.setblocking(False)
        port = sock.getsockname()[1]
        app = server_impl.streamable_http_app(
            stateless_http=True, json_response=True, host="127.0.0.1"
        )
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            for _ in range(100):
                if server.started:
                    break
                await asyncio.sleep(0.01)
            assert server.started
            settings = Settings(mcp_url=f"http://127.0.0.1:{port}/mcp")
            async with connect_mcp(settings) as facade:
                assert facade.protocol_version
                assert facade.server_capabilities.tools is not None
                assert [tool.name for tool in await facade.discover()] == [
                    "search_logs"
                ]
                with pytest.raises(MCPClientError, match="not discovered"):
                    await facade.call("write_file", {"path": "/tmp/x"})
                result = await facade.call("search_logs", {"query": "fake-error"})
                assert result.status == "empty"
            with pytest.raises(MCPClientError, match="call failed"):
                await facade.call("search_logs", {"query": "after-close"})
            assert called == ["fake-error"]
        finally:
            server.should_exit = True
            await task

    asyncio.run(scenario())
