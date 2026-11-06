import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_agent.domain.models import InvestigationContext
from ai_agent.mcp.client import MCPClientError, ToolResult


class ToolRejected(ValueError):
    """The requested tool or its arguments are outside the allowed scope."""


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class IncidentContextArgs(_Args):
    incident_id: str
    investigation_id: str


class SearchLogsArgs(_Args):
    project_id: str
    environment_id: str
    service_ids: list[str]
    from_: datetime = Field(alias="from")
    to: datetime
    query: str = Field(min_length=1, max_length=1500)
    limit: int = Field(ge=1, le=100, strict=True)
    trace_id: str | None = None


class QueryPrometheusArgs(_Args):
    project_id: str
    environment_id: str
    query: str = Field(min_length=1, max_length=1800)
    from_: datetime = Field(alias="from")
    to: datetime
    step_seconds: int = Field(ge=10, le=3600, strict=True)
    max_series: int = Field(ge=1, le=50, strict=True)


class GetTraceArgs(_Args):
    project_id: str
    environment_id: str
    trace_id: str = Field(min_length=8, max_length=128)


SCHEMAS: dict[str, type[_Args]] = {
    "get_incident_context": IncidentContextArgs,
    "search_logs": SearchLogsArgs,
    "query_prometheus": QueryPrometheusArgs,
    "get_trace": GetTraceArgs,
}

_SECRET = re.compile(
    r"(?i)(bearer\s+\S+|(?:password|token|api[_-]?key|secret)\s*[=:]\s*\S+)"
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PROM_SELECTOR = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*\{([^{}]+)\}$")


class ToolTransport(Protocol):
    async def call(self, name: str, arguments: Mapping[str, object]) -> ToolResult: ...


def _clean(text: str, limit: int = 500) -> str:
    text = _SECRET.sub("[REDACTED]", text)
    return _EMAIL.sub("[REDACTED_EMAIL]", text)[:limit]


def _safe_value(value: object) -> object:
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, list):
        return [_safe_value(item) for item in value[:100]]
    if isinstance(value, dict):
        return {str(k)[:80]: _safe_value(v) for k, v in list(value.items())[:30]}
    return value


def _valid_url(url: object) -> bool:
    if url is None:
        return True
    try:
        parts = urlsplit(str(url))
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and parts.username is None
        and parts.password is None
        and not parts.query
        and _SECRET.search(str(url)) is None
        and _EMAIL.search(str(url)) is None
    )


class SafeToolExecutor:
    def __init__(self, context: InvestigationContext, transport: ToolTransport):
        self._context = context
        self._transport = transport

    async def execute(
        self, name: str, arguments: dict[str, object]
    ) -> dict[str, object]:
        schema = SCHEMAS.get(name)
        if schema is None:
            raise ToolRejected("Tool is not in the approved diagnostic vertical")
        try:
            parsed = schema.model_validate(arguments)
            data = parsed.model_dump(mode="json", by_alias=True)
            context = self._context
            for key, expected in (
                ("project_id", context.project_id),
                ("environment_id", context.environment_id),
                ("incident_id", context.incident_id),
                ("investigation_id", context.investigation_id),
            ):
                if key in data and UUID(data[key]) != expected:
                    raise ToolRejected("Action is outside investigation scope")
            for service_id in data.get("service_ids", []):
                if UUID(service_id) not in context.service_ids:
                    raise ToolRejected("Service is outside investigation scope")
            if "from" in data:
                start = parsed.from_
                end = parsed.to
                if (
                    start.tzinfo is None
                    or end.tzinfo is None
                    or start.utcoffset() != timedelta(0)
                    or end.utcoffset() != timedelta(0)
                    or start > end
                    or start < context.window.from_
                    or end > context.window.to
                ):
                    raise ToolRejected("Time window is outside investigation scope")
            if name == "query_prometheus":
                selector = _PROM_SELECTOR.fullmatch(data["query"])
                if selector is None:
                    raise ToolRejected("Only scoped metric selectors are supported")
                labels = {}
                for part in selector.group(1).split(","):
                    matcher = re.fullmatch(
                        r'\s*([A-Za-z_]\w*)="([A-Za-z0-9_-]+)"\s*', part
                    )
                    if matcher is None or matcher.group(1) in labels:
                        raise ToolRejected("Invalid metric selector labels")
                    labels[matcher.group(1)] = matcher.group(2)
                if labels.get("project_id") != str(context.project_id) or labels.get(
                    "environment_id"
                ) != str(context.environment_id):
                    raise ToolRejected("Metric selector lacks exact scope labels")
        except (ValidationError, ValueError, TypeError) as exc:
            raise ToolRejected("Invalid or out-of-scope tool arguments") from exc
        try:
            result = await self._transport.call(name, data)
        except MCPClientError:
            return {
                "status": "error",
                "summary": "Diagnostic source unavailable",
                "source_refs": [],
                "items": [],
                "truncated": False,
                "error": {
                    "code": "source_unavailable",
                    "message": "Diagnostic source unavailable",
                },
            }
        refs = []
        for source in result.source_refs[:100]:
            if not _valid_url(source.url):
                continue
            if source.source_id is None and source.url is None:
                continue
            if _SECRET.search(str(source.source_id)) or _EMAIL.search(
                str(source.source_id)
            ):
                continue
            link = source.model_dump(mode="json")
            link["metadata"] = {}
            refs.append(link)
        items = []
        item_bytes = 0
        for item in result.items[:100]:
            cleaned = _safe_value(item)
            size = len(json.dumps(cleaned, ensure_ascii=False).encode("utf-8"))
            if item_bytes + size > 65536:
                break
            items.append(cleaned)
            item_bytes += size
        return {
            "status": result.status,
            "summary": _clean(result.summary),
            "source_refs": refs,
            "items": items,
            "truncated": result.truncated or len(items) < len(result.items),
            "error": (
                {
                    "code": _clean(result.error.code, 80),
                    "message": _clean(result.error.message),
                }
                if result.error
                else None
            ),
        }
