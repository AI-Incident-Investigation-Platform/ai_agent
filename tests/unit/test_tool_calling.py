import asyncio
import runpy
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, Field

from ai_agent.llm.errors import LLMResponseError
from ai_agent.llm.tool_calling import validate_tool_calls
from ai_agent.llm.types import ChatCompletion, ChatMessage, ToolCall

probe_once = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/smoke_tool_calling.py")
)["probe_once"]


class SearchLogsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1)
    limit: int = Field(ge=1, le=3)


SCHEMAS = {"search_logs": SearchLogsArgs}


def test_valid_native_call_is_returned():
    call = ToolCall("call_1", "search_logs", {"service_id": "payment", "limit": 3})
    assert validate_tool_calls(ChatCompletion(None, (call,)), SCHEMAS) == (call,)


def test_textual_json_is_never_treated_as_a_tool_call():
    completion = ChatCompletion(
        '{"name":"search_logs","arguments":{"service_id":"payment","limit":3}}'
    )
    assert validate_tool_calls(completion, SCHEMAS) == ()


@pytest.mark.parametrize(
    "calls",
    [
        (ToolCall("call_1", "unknown", {"service_id": "payment", "limit": 3}),),
        (ToolCall("", "search_logs", {"service_id": "payment", "limit": 3}),),
        (ToolCall("call_1", "search_logs", {"service_id": "payment"}),),
        (ToolCall("call_1", "search_logs", {"service_id": "payment", "limit": 0}),),
        (ToolCall("call_1", "search_logs", {"service_id": "payment", "limit": "3"}),),
        (
            ToolCall(
                "call_1",
                "search_logs",
                {"service_id": "payment", "limit": 3, "extra": "bad"},
            ),
        ),
        (
            ToolCall("call_1", "search_logs", {"service_id": "payment", "limit": 3}),
            ToolCall("call_1", "search_logs", {"service_id": "payment", "limit": 2}),
        ),
    ],
)
def test_invalid_native_calls_are_rejected(calls):
    with pytest.raises(LLMResponseError):
        validate_tool_calls(ChatCompletion(None, calls), SCHEMAS)


def test_schema_must_reject_unknown_arguments():
    class PermissiveArgs(BaseModel):
        service_id: str

    call = ToolCall("call_1", "search_logs", {"service_id": "payment"})
    with pytest.raises(ValueError, match="forbid extra"):
        validate_tool_calls(
            ChatCompletion(None, (call,)), {"search_logs": PermissiveArgs}
        )


def test_probe_uses_two_fake_read_only_calls_then_direct_answer():
    class FakeProvider:
        def __init__(self):
            self.requests = []

        async def chat(self, messages, *, tools=None):
            self.requests.append((messages, tools))
            if len(self.requests) == 1:
                return ChatCompletion(
                    None,
                    (
                        ToolCall(
                            "call_1",
                            "search_logs",
                            {"service_id": "payment-service", "limit": 3},
                        ),
                    ),
                    "tool_calls",
                )
            if len(self.requests) == 2:
                return ChatCompletion(
                    None,
                    (
                        ToolCall(
                            "call_2",
                            "query_prometheus",
                            {
                                "service_id": "payment-service",
                                "metric": "http_5xx_rate",
                            },
                        ),
                    ),
                    "tool_calls",
                )
            return ChatCompletion("4", (), "stop")

    provider = FakeProvider()
    result = asyncio.run(probe_once(provider))

    assert (result.first, result.second, result.final, result.no_tool) == (
        "native",
        "native",
        "answered",
        "direct",
    )
    history = provider.requests[1][0]
    assert history[2].tool_calls[0].name == "search_logs"
    assert history[3] == ChatMessage(
        "tool",
        '{"status": "ok", "items": ["fictional: connection timeout"]}',
        tool_call_id="call_1",
    )
    assert provider.requests[2][0][-1] == ChatMessage(
        "tool",
        '{"status": "ok", "value": 0.12, "unit": "ratio"}',
        tool_call_id="call_2",
    )


def test_probe_does_not_execute_textual_tool_request():
    class FakeProvider:
        async def chat(self, messages, *, tools=None):
            if messages[0].role == "system":
                return ChatCompletion('{"name":"search_logs"}', (), "stop")
            return ChatCompletion("4", (), "stop")

    result = asyncio.run(probe_once(FakeProvider()))
    assert (result.first, result.second, result.final, result.no_tool) == (
        "text_only",
        "not_attempted",
        "not_attempted",
        "direct",
    )


@pytest.mark.parametrize(
    "call",
    [
        ToolCall("call_1", "unknown", {}),
        ToolCall("call_1", "search_logs", {"service_id": "payment-service"}),
    ],
)
def test_probe_never_executes_invalid_native_call(call):
    class FakeProvider:
        def __init__(self):
            self.requests = []

        async def chat(self, messages, *, tools=None):
            self.requests.append(messages)
            if len(self.requests) == 1:
                return ChatCompletion(None, (call,), "tool_calls")
            return ChatCompletion("4", (), "stop")

    provider = FakeProvider()
    result = asyncio.run(probe_once(provider))
    assert result.first == "invalid_native"
    assert result.second == result.final == "not_attempted"
    assert len(provider.requests) == 2
