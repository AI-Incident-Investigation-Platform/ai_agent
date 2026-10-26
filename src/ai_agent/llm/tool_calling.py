from collections.abc import Mapping

from pydantic import BaseModel, ValidationError

from ai_agent.llm.errors import LLMResponseError
from ai_agent.llm.types import ChatCompletion, ToolCall


def validate_tool_calls(
    completion: ChatCompletion, schemas: Mapping[str, type[BaseModel]]
) -> tuple[ToolCall, ...]:

    validated = []
    seen_ids = set()
    for call in completion.tool_calls:
        schema = schemas.get(call.name)
        if schema is None or not call.id.strip() or call.id in seen_ids:
            raise LLMResponseError("Unknown tool or invalid tool call ID")
        if schema.model_config.get("extra") != "forbid":
            raise ValueError("Tool schemas must forbid extra arguments")
        try:
            arguments = schema.model_validate(call.arguments, strict=True)
        except ValidationError as exc:
            raise LLMResponseError("Tool arguments do not match the schema") from exc
        validated.append(ToolCall(call.id, call.name, arguments.model_dump()))
        seen_ids.add(call.id)
    return tuple(validated)
