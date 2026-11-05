import json
from pathlib import Path

import pytest

from ai_agent.application.contracts import StartAIRequest
from ai_agent.application.mappers import start_from_graph_state, to_graph_state

EXAMPLES = Path(__file__).resolve().parents[3] / "docs/contracts/examples"


def start_request() -> StartAIRequest:
    payload = json.loads((EXAMPLES / "ai-start.request.json").read_text())
    return StartAIRequest.model_validate(payload)


def test_graph_state_round_trip_does_not_depend_on_http():
    request = start_request()
    state = to_graph_state(request)
    assert state["investigation_id"] == str(request.investigation_id)
    assert state["budget"] == request.budget
    assert start_from_graph_state(state) == request


def test_graph_state_requires_matching_context():
    state = to_graph_state(start_request())
    state["investigation_id"] = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(ValueError, match="matching"):
        start_from_graph_state(state)
