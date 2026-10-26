import asyncio
import json

import httpx
import pytest

from ai_agent.core.config import Settings
from ai_agent.llm.errors import (
    LLMHTTPError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTransportError,
)
from ai_agent.llm.providers.llama_cpp import LlamaCppProvider
from ai_agent.llm.types import ChatMessage, ToolCall


def test_chat_uses_openai_compatible_endpoint():
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    settings = Settings(_env_file=None, llm_model="local-model")

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/", transport=httpx.MockTransport(respond)
        ) as client:
            return await LlamaCppProvider(settings, client).chat(
                [ChatMessage("user", "hello")]
            )

    result = asyncio.run(call_chat())

    assert result.content == "ok"
    assert requests[0].url.path == "/v1/chat/completions"
    assert json.loads(requests[0].content) == {
        "model": "local-model",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0,
        "max_tokens": 512,
        "stream": False,
    }


def test_provider_can_be_created_without_connecting_to_server():
    provider = LlamaCppProvider(Settings(_env_file=None))
    assert provider is not None


def test_chat_preserves_system_user_and_assistant_messages():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/", transport=httpx.MockTransport(respond)
        ) as client:
            return await LlamaCppProvider(Settings(_env_file=None), client).chat(
                [
                    ChatMessage("system", "Use only given facts."),
                    ChatMessage("user", "What next?"),
                    ChatMessage("assistant", "Check logs."),
                ]
            )

    assert asyncio.run(call_chat()).content == "ok"
    assert json.loads(requests[0].content)["messages"] == [
        {"role": "system", "content": "Use only given facts."},
        {"role": "user", "content": "What next?"},
        {"role": "assistant", "content": "Check logs."},
    ]


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(503), LLMHTTPError),
        (httpx.Response(200, json={"choices": []}), LLMResponseError),
        (
            httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": ""}}]},
            ),
            LLMResponseError,
        ),
        (
            httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}),
            LLMResponseError,
        ),
        (
            httpx.Response(
                200,
                json={"choices": [{"message": {"role": "user", "content": "ok"}}]},
            ),
            LLMResponseError,
        ),
        (httpx.Response(200, json={"choices": "not a list"}), LLMResponseError),
        (httpx.Response(200, content=b"not json"), LLMResponseError),
        (
            httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "function": {
                                            "name": "lookup_status",
                                            "arguments": "not json",
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            ),
            LLMResponseError,
        ),
        (
            httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": "partial"},
                            "finish_reason": "length",
                        }
                    ]
                },
            ),
            LLMResponseError,
        ),
    ],
)
def test_chat_reports_server_and_response_errors(response, expected):
    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/",
            transport=httpx.MockTransport(lambda _: response),
        ) as client:
            await LlamaCppProvider(Settings(_env_file=None), client).chat(
                [ChatMessage("user", "hello")]
            )

    with pytest.raises(expected) as error:
        asyncio.run(call_chat())
    if expected is LLMHTTPError:
        assert error.value.status_code == 503


def test_chat_reports_transport_error():
    def fail(request):
        raise httpx.ConnectError("connection refused", request=request)

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/", transport=httpx.MockTransport(fail)
        ) as client:
            await LlamaCppProvider(Settings(_env_file=None), client).chat(
                [ChatMessage("user", "hello")]
            )

    with pytest.raises(LLMTransportError):
        asyncio.run(call_chat())


def test_chat_reports_deadline():
    async def slow(_request):
        await asyncio.sleep(0.05)
        return httpx.Response(200)

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/",
            transport=httpx.MockTransport(slow),
        ) as client:
            settings = Settings(_env_file=None, llm_timeout_seconds=0.001)
            await LlamaCppProvider(settings, client).chat(
                [ChatMessage("user", "hello")]
            )

    with pytest.raises(LLMTimeoutError):
        asyncio.run(call_chat())


def test_chat_preserves_structured_tool_call_without_executing_it():
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "lookup_status",
                                    "arguments": '{"incident_id":"inc-1"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
    )

    requests = []

    def respond(request):
        requests.append(request)
        return response

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/",
            transport=httpx.MockTransport(respond),
        ) as client:
            return await LlamaCppProvider(Settings(_env_file=None), client).chat(
                [ChatMessage("user", "hello")],
                tools=[
                    {
                        "type": "function",
                        "function": {"name": "lookup_status", "parameters": {}},
                    }
                ],
            )

    completion = asyncio.run(call_chat())
    assert completion.content is None
    assert completion.tool_calls[0].name == "lookup_status"
    assert completion.tool_calls[0].arguments == {"incident_id": "inc-1"}
    assert json.loads(requests[0].content)["tools"][0]["function"]["name"] == (
        "lookup_status"
    )


def test_chat_serializes_native_tool_exchange():
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/", transport=httpx.MockTransport(respond)
        ) as client:
            return await LlamaCppProvider(Settings(_env_file=None), client).chat(
                [
                    ChatMessage("user", "Check logs"),
                    ChatMessage(
                        "assistant",
                        None,
                        tool_calls=(ToolCall("call_1", "search_logs", {"limit": 3}),),
                    ),
                    ChatMessage("tool", '{"status":"ok"}', tool_call_id="call_1"),
                ]
            )

    assert asyncio.run(call_chat()).content == "ok"
    assert requests[0]["messages"] == [
        {"role": "user", "content": "Check logs"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "search_logs", "arguments": '{"limit": 3}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"status":"ok"}'},
    ]


def test_chat_accepts_object_arguments_from_llama_server():
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "search_logs",
                                    "arguments": {"limit": 3},
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )

    async def call_chat():
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/",
            transport=httpx.MockTransport(lambda _: response),
        ) as client:
            return await LlamaCppProvider(Settings(_env_file=None), client).chat(
                [ChatMessage("user", "Check logs")]
            )

    assert asyncio.run(call_chat()).tool_calls == (
        ToolCall("call_1", "search_logs", {"limit": 3}),
    )
