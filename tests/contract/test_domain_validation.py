import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_agent.application.contracts import AIResultCallback, Problem, StartAIRequest

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/contracts/examples"


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_utc_and_ordered_window_required():
    payload = example("ai-start.request.json")
    payload["detected_at"] = "2026-10-19T17:35:00+03:00"
    with pytest.raises(ValidationError, match="UTC"):
        StartAIRequest.model_validate(payload)

    payload = example("ai-start.request.json")
    payload["window"]["from"] = "2026-10-19T15:00:00Z"
    with pytest.raises(ValidationError, match="start"):
        StartAIRequest.model_validate(payload)


def test_result_outcome_and_scope_must_match_report():
    payload = example("ai-result.callback.json")
    payload["report"]["outcome"] = "inconclusive"
    with pytest.raises(ValidationError, match="matching report"):
        AIResultCallback.model_validate(payload)

    payload = example("ai-result.callback.json")
    payload["report"]["incident_id"] = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    with pytest.raises(ValidationError, match="Report IDs"):
        AIResultCallback.model_validate(payload)

    payload = example("ai-result.callback.json")
    payload["evidence"][0]["investigation_id"] = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    with pytest.raises(ValidationError, match="Evidence must belong"):
        AIResultCallback.model_validate(payload)


def test_problem_rejects_unknown_fields_and_null_error_list():
    payload = {
        "type": "about:blank",
        "title": "Invalid request",
        "status": 422,
        "code": "validation_error",
        "detail": "Invalid payload",
        "request_id": "request-1",
    }
    assert Problem.model_validate(payload).errors == []
    with pytest.raises(ValidationError):
        Problem.model_validate({**payload, "errors": None})
    with pytest.raises(ValidationError):
        Problem.model_validate({**payload, "secret": "unexpected"})
