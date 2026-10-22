"""OpenAI-compatible chat adapter for a local llama.cpp server."""

import asyncio
import json
from collections.abc import Sequence
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from ai_agent.core.config import Settings
from ai_agent.llm.errors import (
    LLMHTTPError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTransportError,
)
from ai_agent.llm.types import ChatCompletion, ChatMessage, ToolCall


class _FunctionCall(BaseModel):
    name: str = Field(min_length=1)
    arguments: str


class _ResponseToolCall(BaseModel):
    id: str = Field(min_length=1)
    function: _FunctionCall


class _ResponseMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None
    tool_calls: list[_ResponseToolCall] | None = None


class _ResponseChoice(BaseModel):
    message: _ResponseMessage
    finish_reason: str | None = None


class _ChatResponse(BaseModel):
    choices: list[_ResponseChoice] = Field(min_length=1)


class LlamaCppProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._client = client

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        tools: Sequence[dict[str, object]] | None = None,
    ) -> ChatCompletion:
        if not messages:
            raise ValueError("At least one chat message is required")

        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._settings.llm_max_tokens,
            "stream": False,
        }
        if tools is not None:
            payload["tools"] = list(tools)
        try:
            async with asyncio.timeout(self._settings.llm_timeout_seconds):
                if self._client is not None:
                    return await self._request(self._client, payload)
                timeout = httpx.Timeout(
                    self._settings.llm_timeout_seconds,
                    connect=self._settings.llm_connect_timeout_seconds,
                )
                async with httpx.AsyncClient(
                    base_url=self._settings.llm_base_url.rstrip("/") + "/",
                    timeout=timeout,
                ) as client:
                    return await self._request(client, payload)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise LLMTimeoutError("Local inference request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMHTTPError(exc.response.status_code) from exc
        except httpx.RequestError as exc:
            raise LLMTransportError("Local inference server is unavailable") from exc

    @staticmethod
    async def _request(
        client: httpx.AsyncClient, payload: dict[str, object]
    ) -> ChatCompletion:
        response = await client.post("chat/completions", json=payload)
        response.raise_for_status()
        try:
            choice = _ChatResponse.model_validate(response.json()).choices[0]
            message = choice.message
            tool_calls = []
            for item in message.tool_calls or []:
                arguments = json.loads(item.function.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be an object")
                tool_calls.append(ToolCall(item.id, item.function.name, arguments))
            finish_reason = choice.finish_reason
            if finish_reason == "length":
                raise LLMResponseError("Local inference output was truncated")
            if not message.content and not tool_calls:
                raise LLMResponseError("Local inference returned no content")
            return ChatCompletion(message.content, tuple(tool_calls), finish_reason)
        except (ValidationError, ValueError) as exc:
            raise LLMResponseError("Invalid local inference response") from exc
