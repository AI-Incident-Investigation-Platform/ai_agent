import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from ai_agent.core.config import Settings
from ai_agent.llm.errors import LLMError, LLMResponseError
from ai_agent.llm.providers.llama_cpp import LlamaCppProvider
from ai_agent.llm.tool_calling import validate_tool_calls
from ai_agent.llm.types import ChatCompletion, ChatMessage, ChatProvider, ToolCall


class SearchLogsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: Literal["payment-service"]
    limit: Literal[3]


class QueryPrometheusArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: Literal["http_5xx_rate"]
    service_id: Literal["payment-service"]


SCHEMAS: dict[str, type[BaseModel]] = {
    "search_logs": SearchLogsArgs,
    "query_prometheus": QueryPrometheusArgs,
}
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema.model_json_schema(),
        },
    }
    for name, schema, description in (
        ("search_logs", SearchLogsArgs, "Read three fictional service log excerpts."),
        (
            "query_prometheus",
            QueryPrometheusArgs,
            "Read one fictional service error-rate metric.",
        ),
    )
]


@dataclass(frozen=True)
class ProbeResult:
    first: str
    second: str
    final: str
    no_tool: str
    first_shape: dict[str, object]


def _shape(completion: ChatCompletion) -> dict[str, object]:
    return {
        "finish_reason": completion.finish_reason,
        "content": (completion.content or "")[:180],
        "tool_calls": [
            {"id": call.id, "name": call.name, "arguments": call.arguments}
            for call in completion.tool_calls
        ],
    }


def _expected_call(
    completion: ChatCompletion, expected: str
) -> tuple[str, ToolCall | None]:
    try:
        calls = validate_tool_calls(completion, SCHEMAS)
    except LLMResponseError:
        return "invalid_native", None
    if len(calls) != 1 or calls[0].name != expected:
        return ("text_only" if not calls else "wrong_tool"), None
    return "native", calls[0]


def _fake_result(call: ToolCall) -> str:
    if call.name == "search_logs":
        return json.dumps({"status": "ok", "items": ["fictional: connection timeout"]})
    if call.name == "query_prometheus":
        return json.dumps({"status": "ok", "value": 0.12, "unit": "ratio"})
    raise ValueError("Only the two validated fake tools may be executed")


async def probe_once(provider: ChatProvider) -> ProbeResult:
    messages = [
        ChatMessage(
            "system", "Use tools for fictional diagnostics; do not invent data."
        ),
        ChatMessage(
            "user",
            "Call search_logs for payment-service with limit 3. Do not call "
            "query_prometheus yet.",
        ),
    ]
    first = await provider.chat(messages, tools=TOOLS)
    first_status, first_call = _expected_call(first, "search_logs")
    second_status = "not_attempted"
    final_status = "not_attempted"
    if first_call is not None:
        messages.extend(
            [
                ChatMessage("assistant", first.content, tool_calls=(first_call,)),
                ChatMessage(
                    "tool",
                    _fake_result(first_call),
                    tool_call_id=first_call.id,
                ),
                ChatMessage(
                    "user",
                    "Now call query_prometheus for payment-service with "
                    'metric="http_5xx_rate".',
                ),
            ]
        )
        second = await provider.chat(messages, tools=TOOLS)
        second_status, second_call = _expected_call(second, "query_prometheus")
        if second_call is not None:
            messages.extend(
                [
                    ChatMessage("assistant", second.content, tool_calls=(second_call,)),
                    ChatMessage(
                        "tool", _fake_result(second_call), tool_call_id=second_call.id
                    ),
                ]
            )
            final = await provider.chat(messages)
            final_status = (
                "answered"
                if final.content and not final.tool_calls
                else "invalid_final"
            )

    no_tool = await provider.chat(
        [ChatMessage("user", "What is 2 + 2? Answer directly without tools.")],
        tools=TOOLS,
    )
    try:
        no_tool_calls = validate_tool_calls(no_tool, SCHEMAS)
        content = no_tool.content or ""
        if no_tool_calls:
            no_tool_status = "tool_used"
        elif any(name in content for name in SCHEMAS) or "<tool_call>" in content:
            no_tool_status = "textual_tool_request"
        else:
            no_tool_status = "direct" if content else "empty"
    except LLMResponseError:
        no_tool_status = "invalid_native"
    return ProbeResult(
        first_status, second_status, final_status, no_tool_status, _shape(first)
    )


async def main(repetitions: int) -> int:
    settings = Settings()
    try:
        async with httpx.AsyncClient(
            base_url=settings.llm_base_url.rstrip("/") + "/",
            timeout=settings.llm_connect_timeout_seconds,
        ) as client:
            models_response = await client.get("models")
            models_response.raise_for_status()
            model_ids = [
                item.get("id") for item in models_response.json().get("data", [])
            ]
            if settings.llm_model not in model_ids:
                print("Configured model is absent from /v1/models", file=sys.stderr)
                return 2
            props_url = settings.llm_base_url.rstrip("/").removesuffix("/v1") + "/props"
            props_response = await client.get(props_url)
            props_response.raise_for_status()
            props = props_response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        print(f"llama-server unavailable: {type(exc).__name__}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "model": settings.llm_model,
                "server_build": props.get("build_info"),
                "chat_template_caps": props.get("chat_template_caps"),
                "template_contains_tool_call": "<tool_call>"
                in props.get("chat_template", ""),
                "repetitions": repetitions,
            }
        )
    )
    results = []
    provider = LlamaCppProvider(settings)
    for attempt in range(1, repetitions + 1):
        try:
            result = await probe_once(provider)
        except LLMError as exc:
            print(json.dumps({"attempt": attempt, "error": type(exc).__name__}))
            continue
        results.append(result)
        print(
            json.dumps(
                {
                    "attempt": attempt,
                    "first": result.first,
                    "second": result.second,
                    "final": result.final,
                    "no_tool": result.no_tool,
                    "first_shape": result.first_shape,
                },
                ensure_ascii=False,
            )
        )

    first_ok = sum(item.first == "native" for item in results)
    sequence_ok = sum(item.second == "native" for item in results)
    no_tool_ok = sum(item.no_tool == "direct" for item in results)
    print(
        json.dumps(
            {
                "first_native": first_ok,
                "two_step_native": sequence_ok,
                "direct_no_tool": no_tool_ok,
                "attempts": repetitions,
            }
        )
    )
    return 0 if first_ok == sequence_ok == no_tool_ok == repetitions else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    raise SystemExit(asyncio.run(main(args.repetitions)))
