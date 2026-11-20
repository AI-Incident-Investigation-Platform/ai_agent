import re
from datetime import datetime, timedelta
from typing import Literal
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_agent.domain.models import (
    Evidence,
    Hypothesis,
    InvestigationContext,
    SourceLink,
)

_SOURCE_TYPES = {
    "search_logs": {"elasticsearch", "loki"},
    "query_prometheus": {"prometheus"},
    "get_trace": {"tempo"},
    "get_incident_context": {"manual"},
}
_SAFE_ID = re.compile(r"[A-Za-z0-9._:/#-]{1,256}\Z")


def _in_window(value: object, context: InvestigationContext) -> bool:
    if not isinstance(value, str):
        return False
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (
        stamp.tzinfo is not None
        and stamp.utcoffset() == timedelta(0)
        and context.window.from_ <= stamp <= context.window.to
    )


def _valid_source(source: SourceLink, context: InvestigationContext) -> bool:
    if not source.source_id or not _SAFE_ID.fullmatch(source.source_id):
        return False
    if source.observed_at and not (
        context.window.from_ <= source.observed_at <= context.window.to
    ):
        return False
    for key, expected in (
        ("project_id", context.project_id),
        ("environment_id", context.environment_id),
        ("incident_id", context.incident_id),
        ("investigation_id", context.investigation_id),
    ):
        if key in source.metadata and str(source.metadata[key]) != str(expected):
            return False
    if "service_id" in source.metadata and str(source.metadata["service_id"]) not in {
        str(item) for item in context.service_ids
    }:
        return False
    if source.url is not None:
        url = urlsplit(str(source.url))
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
        ):
            return False
    return True


def safe_source_refs(
    candidates: object, context: InvestigationContext
) -> list[dict[str, object]]:
    if not isinstance(candidates, list):
        return []
    refs = []
    for candidate in candidates:
        try:
            source = SourceLink.model_validate(candidate)
        except ValidationError:
            continue
        if _valid_source(source, context):
            refs.append(
                source.model_copy(update={"metadata": {}}).model_dump(mode="json")
            )
    return refs


def _matching_items(
    name: str,
    source: SourceLink,
    items: list[object],
    context: InvestigationContext,
    arguments: dict[str, object],
) -> list[dict[str, object]]:
    matched = []
    requested = arguments.get("service_ids", [])
    if not requested and "service_id" in arguments:
        requested = [arguments["service_id"]]
    allowed_services = (
        {str(value) for value in requested}
        if requested
        else {str(value) for value in context.service_ids}
    )
    for item in items:
        if not isinstance(item, dict):
            continue
        if "service_id" in item and str(item["service_id"]) not in allowed_services:
            continue
        if name == "search_logs":
            valid = item.get("log_id") == source.source_id and _in_window(
                item.get("timestamp"), context
            )
        elif name == "get_trace":
            valid = (
                source.source_id == arguments.get("trace_id")
                and bool(item.get("span_id"))
                and _in_window(item.get("started_at"), context)
            )
        elif name == "query_prometheus":
            labels = item.get("labels")
            points = item.get("points")
            valid = (
                isinstance(labels, dict)
                and labels.get("project_id") == str(context.project_id)
                and labels.get("environment_id") == str(context.environment_id)
                and isinstance(points, list)
                and bool(points)
                and all(
                    isinstance(point, dict) and _in_window(point.get("at"), context)
                    for point in points
                )
            )
        elif name == "get_incident_context":
            valid = item.get("incident_id") == str(context.incident_id)
        else:
            valid = False
        if valid:
            matched.append(item)
    return matched


def collect_evidence(
    context: InvestigationContext,
    action: dict[str, object],
    result: dict[str, object],
    existing: list[dict[str, object]],
    *,
    collected_at: datetime,
) -> list[dict[str, object]]:
    evidence = list(existing)
    name = action.get("name")
    arguments = action.get("arguments")
    if (
        name not in _SOURCE_TYPES
        or not isinstance(arguments, dict)
        or result.get("status") not in {"ok", "partial"}
        or not isinstance(result.get("items"), list)
        or not result["items"]
        or not isinstance(result.get("source_refs"), list)
    ):
        return evidence
    if name == "get_incident_context":
        if arguments.get("incident_id") != str(context.incident_id) or arguments.get(
            "investigation_id"
        ) != str(context.investigation_id):
            return evidence
    elif arguments.get("project_id") != str(context.project_id) or arguments.get(
        "environment_id"
    ) != str(context.environment_id):
        return evidence
    if name in {"search_logs", "query_prometheus"}:
        start = arguments.get("from")
        end = arguments.get("to")
        if not _in_window(start, context) or not _in_window(end, context):
            return evidence
        if datetime.fromisoformat(
            start.replace("Z", "+00:00")
        ) > datetime.fromisoformat(end.replace("Z", "+00:00")):
            return evidence
    requested_services = arguments.get("service_ids", [])
    if not requested_services and "service_id" in arguments:
        requested_services = [arguments["service_id"]]
    if not isinstance(requested_services, list) or any(
        str(service_id) not in {str(item) for item in context.service_ids}
        for service_id in requested_services
    ):
        return evidence
    known_ids = {item["id"] for item in existing}
    for candidate in result["source_refs"]:
        try:
            source = SourceLink.model_validate(candidate)
        except ValidationError:
            continue
        if source.source_type not in _SOURCE_TYPES[name] or not _valid_source(
            source, context
        ):
            continue
        if (
            "service_id" in source.metadata
            and requested_services
            and str(source.metadata["service_id"]) not in requested_services
        ):
            continue
        matched = _matching_items(name, source, result["items"], context, arguments)
        if not matched:
            continue
        evidence_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{context.investigation_id}:{name}:{source.source_type}:{source.source_id}",
            )
        )
        if evidence_id in known_ids:
            continue
        known_ids.add(evidence_id)
        reported_services = {
            str(item["service_id"]) for item in matched if "service_id" in item
        }
        if reported_services:
            service_ids = [UUID(service_id) for service_id in sorted(reported_services)]
        elif len(requested_services) == 1:
            service_ids = [UUID(requested_services[0])]
        else:
            service_ids = []
        record = Evidence(
            id=UUID(evidence_id),
            investigation_id=context.investigation_id,
            source=source.model_copy(update={"metadata": {}}),
            title=f"{name}: {source.source_type}",
            summary=f"{len(matched)} record(s) from {name}",
            excerpt=None,
            service_ids=service_ids,
            hypothesis_ids=[],
            collected_at=collected_at,
            confidence_note=(
                "Источник вернул неполные данные"
                if result["status"] == "partial" or result.get("truncated")
                else None
            ),
        )
        evidence.append(record.model_dump(mode="json"))
    return evidence


class _HypothesisProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    explanation: str = Field(min_length=1, max_length=1000)
    evidence_for_ids: list[UUID]
    evidence_against_ids: list[UUID]
    confidence: Literal["high", "medium", "low"]


def update_hypotheses(
    context: InvestigationContext,
    proposals: list[dict[str, object]],
    evidence: list[dict[str, object]],
    *,
    updated_at: datetime,
) -> tuple[list[dict[str, object]], dict[str, dict[str, list[str]]]]:
    if len(proposals) > 3:
        raise ValueError("No more than three hypotheses are allowed")
    evidence_by_id = {}
    for item in evidence:
        parsed = Evidence.model_validate(item)
        if (
            parsed.investigation_id != context.investigation_id
            or not _valid_source(parsed.source, context)
            or any(service not in context.service_ids for service in parsed.service_ids)
        ):
            raise ValueError("Out-of-scope evidence")
        evidence_by_id[parsed.id] = parsed
    hypotheses = []
    relations = {}
    seen_titles = set()
    for raw in proposals:
        proposal = _HypothesisProposal.model_validate(raw)
        if proposal.title in seen_titles:
            raise ValueError("Duplicate hypothesis")
        seen_titles.add(proposal.title)
        supporting = proposal.evidence_for_ids
        opposing = proposal.evidence_against_ids
        if any(item not in evidence_by_id for item in [*supporting, *opposing]):
            raise ValueError("Unknown evidence reference")
        if set(supporting) & set(opposing):
            raise ValueError("Evidence cannot support and oppose the same hypothesis")
        all_ids = list(dict.fromkeys([*supporting, *opposing]))
        hypothesis_id = uuid5(
            NAMESPACE_URL, f"{context.investigation_id}:hypothesis:{proposal.title}"
        )
        record = Hypothesis(
            id=hypothesis_id,
            investigation_id=context.investigation_id,
            title=proposal.title,
            explanation=proposal.explanation,
            status="pending",
            confidence="low",
            evidence_ids=all_ids,
            updated_at=updated_at,
        )
        hypotheses.append(record.model_dump(mode="json"))
        relations[str(hypothesis_id)] = {
            "for": [str(item) for item in supporting],
            "against": [str(item) for item in opposing],
        }
    return hypotheses, relations


def link_evidence(
    evidence: list[dict[str, object]], hypotheses: list[dict[str, object]]
) -> list[dict[str, object]]:
    links: dict[UUID, list[UUID]] = {}
    for item in hypotheses:
        hypothesis = Hypothesis.model_validate(item)
        for evidence_id in hypothesis.evidence_ids:
            links.setdefault(evidence_id, []).append(hypothesis.id)
    return [
        record.model_copy(
            update={"hypothesis_ids": links.get(record.id, [])}
        ).model_dump(mode="json")
        for record in (Evidence.model_validate(item) for item in evidence)
    ]
