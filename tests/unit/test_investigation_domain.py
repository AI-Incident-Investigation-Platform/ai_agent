import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_agent.agent.graph import build_graph
from ai_agent.application.contracts import AIResultCallback, Problem, StartAIRequest
from ai_agent.application.mappers import start_from_graph_state, to_graph_state
from ai_agent.domain.lifecycle import (
    InvestigationStatus,
    require_new_retry,
    transition_status,
)

EXAMPLES = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "examples"


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_graph_state_round_trip_does_not_depend_on_http():
    request = StartAIRequest.model_validate(example("ai-start.request.json"))
    state = to_graph_state(request)
    assert state["investigation_id"] == str(request.investigation_id)
    assert build_graph().invoke(state) == state
    assert start_from_graph_state(state) == request


def test_graph_state_requires_matching_context():
    request = StartAIRequest.model_validate(example("ai-start.request.json"))
    state = to_graph_state(request)
    state["investigation_id"] = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(ValueError, match="matching"):
        start_from_graph_state(state)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (InvestigationStatus.PENDING, InvestigationStatus.RUNNING),
        (InvestigationStatus.PENDING, InvestigationStatus.CANCELED),
        (InvestigationStatus.RUNNING, InvestigationStatus.COMPLETED),
        (InvestigationStatus.RUNNING, InvestigationStatus.INCONCLUSIVE),
        (InvestigationStatus.RUNNING, InvestigationStatus.FAILED),
        (InvestigationStatus.RUNNING, InvestigationStatus.TIMED_OUT),
        (InvestigationStatus.RUNNING, InvestigationStatus.CANCELED),
    ],
)
def test_allowed_status_transitions(current, target):
    assert transition_status(current, target) == target
    assert transition_status(target, target) == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (InvestigationStatus.PENDING, InvestigationStatus.COMPLETED),
        (InvestigationStatus.RUNNING, InvestigationStatus.PENDING),
        (InvestigationStatus.COMPLETED, InvestigationStatus.FAILED),
        (InvestigationStatus.CANCELED, InvestigationStatus.RUNNING),
    ],
)
def test_illegal_and_terminal_to_terminal_transitions_rejected(current, target):
    with pytest.raises(ValueError, match="Illegal"):
        transition_status(current, target)


def test_retry_requires_new_id_next_attempt_and_parent():
    previous = UUID("22222222-2222-4222-8222-222222222222")
    new = UUID("33333333-3333-4333-8333-333333333333")
    require_new_retry(previous, 1, new, 2, previous)
    for candidate in ((previous, 2, previous), (new, 1, previous), (new, 2, None)):
        with pytest.raises(ValueError, match="Retry"):
            require_new_retry(previous, 1, *candidate)


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
