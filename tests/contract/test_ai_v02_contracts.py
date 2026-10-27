"""Cross-check draft JSON Schemas against transport-neutral Pydantic DTOs."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from ai_agent.application.contracts import (
    AIResultCallback,
    InvestigationEvent,
    Problem,
    StartAIRequest,
)
from ai_agent.domain.models import (
    Evidence,
    ExecutionBudget,
    Hypothesis,
    Investigation,
    RCAReport,
)

CONTRACTS = Path(__file__).resolve().parents[2] / "docs" / "contracts"
FORMAT_CHECKER = FormatChecker()


def load_json(relative_path: str) -> dict:
    return json.loads((CONTRACTS / relative_path).read_text(encoding="utf-8"))


def validate_schema(payload: dict, schema: dict) -> None:
    Draft202012Validator(schema, format_checker=FORMAT_CHECKER).validate(payload)


@pytest.mark.parametrize(
    ("example", "schema", "model"),
    [
        ("ai-start.request.json", "ai-start-request.schema.json", StartAIRequest),
        ("ai-event.tool-completed.json", "ai-events.schema.json", InvestigationEvent),
        ("ai-result.callback.json", "ai-result-callback.schema.json", AIResultCallback),
        ("rca-report.json", "rca-report.schema.json", RCAReport),
    ],
)
def test_canonical_examples_round_trip_through_dto(example, schema, model):
    payload = load_json(f"examples/{example}")
    contract = load_json(f"schemas/{schema}")
    validate_schema(payload, contract)

    parsed = model.model_validate(payload)
    exported = parsed.model_dump(mode="json", by_alias=True)
    validate_schema(exported, contract)
    assert model.model_validate(exported) == parsed


@pytest.mark.parametrize(
    ("definition", "model", "example", "extract"),
    [
        ("ExecutionBudget", ExecutionBudget, "ai-start.request.json", "budget"),
        ("Hypothesis", Hypothesis, "ai-result.callback.json", "hypotheses"),
        ("Evidence", Evidence, "ai-result.callback.json", "evidence"),
        ("RCAReport", RCAReport, "ai-result.callback.json", "report"),
    ],
)
def test_domain_definitions_match_examples(definition, model, example, extract):
    payload = load_json(f"examples/{example}")[extract]
    if isinstance(payload, list):
        payload = payload[0]
    domain_schema = load_json("schemas/domain.schema.json")
    ref_schema = {**domain_schema, "$ref": f"#/$defs/{definition}"}
    validate_schema(payload, ref_schema)
    parsed = model.model_validate(payload)
    validate_schema(parsed.model_dump(mode="json"), ref_schema)


def test_investigation_and_problem_match_domain_definitions():
    request = load_json("examples/ai-start.request.json")
    investigation = {
        "id": request["investigation_id"],
        "incident_id": request["incident_id"],
        "project_id": request["project_id"],
        "environment_id": request["environment_id"],
        "status": "pending",
        "created_at": request["detected_at"],
        "attempt": 1,
        "current_step": 0,
        "tool_calls_count": 0,
        "budget": request["budget"],
    }
    problem = {
        "type": "about:blank",
        "title": "Invalid request",
        "status": 422,
        "code": "validation_error",
        "detail": "Invalid payload",
        "request_id": "request-1",
    }
    domain_schema = load_json("schemas/domain.schema.json")
    for name, payload, model in (
        ("Investigation", investigation, Investigation),
        ("Problem", problem, Problem),
    ):
        ref_schema = {**domain_schema, "$ref": f"#/$defs/{name}"}
        validate_schema(payload, ref_schema)
        validate_schema(
            model.model_validate(payload).model_dump(mode="json"), ref_schema
        )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("investigation_id", "not-a-uuid"),
        ("detected_at", "yesterday"),
        ("schema_version", "2.0"),
        ("attempt", 0),
    ],
)
def test_invalid_start_payload_rejected_by_schema_and_dto(field, bad_value):
    payload = load_json("examples/ai-start.request.json")
    payload[field] = bad_value
    schema = load_json("schemas/ai-start-request.schema.json")
    with pytest.raises(SchemaValidationError):
        validate_schema(payload, schema)
    with pytest.raises(ValidationError):
        StartAIRequest.model_validate(payload)


def test_invalid_event_payload_rejected_by_schema_and_dto():
    payload = load_json("examples/ai-event.tool-completed.json")
    del payload["data"]["tool_call_id"]
    schema = load_json("schemas/ai-events.schema.json")
    with pytest.raises(SchemaValidationError):
        validate_schema(payload, schema)
    with pytest.raises(ValidationError):
        InvestigationEvent.model_validate(payload)


def test_completed_result_requires_report():
    payload = load_json("examples/ai-result.callback.json")
    payload["report"] = None
    schema = load_json("schemas/ai-result-callback.schema.json")
    with pytest.raises(SchemaValidationError):
        validate_schema(payload, schema)
    with pytest.raises(ValidationError):
        AIResultCallback.model_validate(payload)


def test_failed_result_may_omit_report():
    payload = load_json("examples/ai-result.callback.json")
    payload.update(status="failed", report=None, hypotheses=[], evidence=[])
    schema = load_json("schemas/ai-result-callback.schema.json")
    validate_schema(payload, schema)
    assert AIResultCallback.model_validate(payload).report is None


def test_draft_schema_does_not_limit_hypothesis_count_but_dto_does():
    payload = load_json("examples/ai-result.callback.json")
    payload["hypotheses"] = [deepcopy(payload["hypotheses"][0]) for _ in range(4)]
    validate_schema(payload, load_json("schemas/ai-result-callback.schema.json"))
    with pytest.raises(ValidationError):
        AIResultCallback.model_validate(payload)


def test_draft_schema_allows_missing_evidence_locator():
    payload = load_json("examples/ai-result.callback.json")["evidence"][0]
    payload["source"].pop("source_id")
    payload["source"].pop("url")
    domain_schema = load_json("schemas/domain.schema.json")
    validate_schema(payload, {**domain_schema, "$ref": "#/$defs/Evidence"})
    # Contract gap: AI-07 must agree the provenance rule before tightening this DTO.
    assert Evidence.model_validate(payload).source.source_id is None


def test_draft_schema_allows_non_utc_and_unordered_window():
    schema = load_json("schemas/ai-start-request.schema.json")
    payload = load_json("examples/ai-start.request.json")
    payload["detected_at"] = "2026-10-19T17:35:00+03:00"
    validate_schema(payload, schema)
    with pytest.raises(ValidationError):
        StartAIRequest.model_validate(payload)

    payload = load_json("examples/ai-start.request.json")
    payload["window"]["from"] = "2026-10-19T15:00:00Z"
    validate_schema(payload, schema)
    with pytest.raises(ValidationError):
        StartAIRequest.model_validate(payload)


def test_draft_schema_allows_mismatched_report_outcome():
    payload = load_json("examples/ai-result.callback.json")
    payload["report"]["outcome"] = "inconclusive"
    validate_schema(payload, load_json("schemas/ai-result-callback.schema.json"))
    with pytest.raises(ValidationError):
        AIResultCallback.model_validate(payload)
