import asyncio

import pytest

from ai_agent.agent.graph import build_llm_probe_graph
from ai_agent.application.services.llm_probe import run_llm_probe
from ai_agent.llm.errors import LLMResponseError
from ai_agent.llm.types import ChatCompletion, ChatMessage, ToolCall


class FakeProvider:
    def __init__(self, result: ChatCompletion):
        self.result = result
        self.messages: list[ChatMessage] = []

    async def chat(self, messages, *, tools=None):
        self.messages = list(messages)
        return self.result


def test_probe_invokes_provider_through_langgraph():
    provider = FakeProvider(ChatCompletion("READY"))
    assert asyncio.run(run_llm_probe("  Say READY  ", provider)) == "READY"
    assert provider.messages == [ChatMessage("user", "Say READY")]


def test_graph_updates_state_with_model_response():
    provider = FakeProvider(ChatCompletion("Check PostgreSQL pool saturation."))
    state = asyncio.run(build_llm_probe_graph(provider).ainvoke({"prompt": "Next?"}))
    assert state == {
        "prompt": "Next?",
        "response": "Check PostgreSQL pool saturation.",
    }


def test_probe_rejects_empty_prompt():
    provider = FakeProvider(ChatCompletion("unused"))
    with pytest.raises(ValueError, match="empty"):
        asyncio.run(run_llm_probe("  ", provider))
    assert provider.messages == []


def test_probe_does_not_execute_tool_calls():
    provider = FakeProvider(ChatCompletion(None, (ToolCall("id", "tool", {}),)))
    with pytest.raises(LLMResponseError, match="Tool calls"):
        asyncio.run(run_llm_probe("test", provider))
