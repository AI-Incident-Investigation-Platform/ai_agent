import asyncio
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from ai_agent.agent.decisions import ActionDecision, FinishDecision
from ai_agent.agent.graph import build_graph
from ai_agent.application.contracts import StartAIRequest
from ai_agent.application.mappers import to_graph_state

EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "docs/contracts/examples/ai-start.request.json"
)


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    environment_id: str
    service_id: str
    query: str


def state(max_steps=20, max_tool_calls=40):
    payload = json.loads(EXAMPLE.read_text())
    payload["budget"]["max_steps"] = max_steps
    payload["budget"]["max_tool_calls"] = max_tool_calls
    return to_graph_state(StartAIRequest.model_validate(payload))


def action(current, call_id="one", **overrides):
    context = current["context"]
    arguments = {
        "project_id": str(context.project_id),
        "environment_id": str(context.environment_id),
        "service_id": str(context.service_ids[0]),
        "query": "error",
    }
    arguments.update(overrides)
    return ActionDecision(
        kind="action", tool_call_id=call_id, name="search_logs", arguments=arguments
    )


class FakeDecision:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    async def decide(self, current):
        item = next(self.decisions)
        return item(current) if callable(item) else item


class FakeExecutor:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {
            "status": "ok",
            "summary": "sensitive raw log",
            "source_refs": [],
            "items": [],
            "truncated": False,
            "error": None,
        }

    async def execute(self, name, arguments):
        self.calls.append((name, arguments))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def run(decisions, executor=None, *, current=None):
    executor = executor or FakeExecutor()
    current = current or state()
    graph = build_graph(FakeDecision(decisions), executor, {"search_logs": SearchArgs})
    return asyncio.run(graph.ainvoke(current)), executor


def test_finish_without_tools_and_deterministic_replay():
    first, executor = run([FinishDecision(kind="finish", reason="No action needed")])
    second, _ = run([FinishDecision(kind="finish", reason="No action needed")])
    assert first == second
    assert first["terminal_status"] == "ready_for_finalization"
    assert first["step"] == 1
    assert executor.calls == []


def test_two_sequential_tools_and_safe_summary():
    final, executor = run(
        [
            lambda current: action(current),
            lambda current: action(current, "two", query="timeout"),
            FinishDecision(kind="finish", reason="Enough observations"),
        ]
    )
    assert len(executor.calls) == 2
    assert final["step"] == 3
    assert final["tool_calls_count"] == 2
    assert len(final["observations"]) == 2
    assert "sensitive raw log" not in str(final["event_summaries"])


@pytest.mark.parametrize(
    "decision, reason",
    [
        (
            lambda current: action(current, service_id="other"),
            "invalid_or_out_of_scope_action",
        ),
        (
            lambda current: action(current, extra="bad"),
            "invalid_or_out_of_scope_action",
        ),
        (
            lambda current: action(current, project_id="other"),
            "invalid_or_out_of_scope_action",
        ),
        (
            ActionDecision(
                kind="action", tool_call_id="x", name="unknown", arguments={}
            ),
            "unavailable_tool",
        ),
    ],
)
def test_rejected_action_never_reaches_executor(decision, reason):
    final, executor = run([decision])
    assert final["terminal_reason"] == reason
    assert executor.calls == []


def test_invalid_decision_repairs_once_then_inconclusive():
    final, executor = run(['{"kind":"action"}', {"kind": "action"}])
    assert final["terminal_reason"] == "invalid_decision"
    assert final["step"] == 1
    assert executor.calls == []


def test_repeated_action_stops_loop():
    final, executor = run(
        [lambda current: action(current), lambda current: action(current, "two")]
    )
    assert final["terminal_reason"] == "invalid_or_out_of_scope_action"
    assert len(executor.calls) == 1


@pytest.mark.parametrize("status", ["empty", "partial", "error"])
def test_non_ok_tool_observation_is_preserved(status):
    executor = FakeExecutor(
        {
            "status": status,
            "summary": "private text",
            "source_refs": [],
            "items": [],
            "truncated": status == "partial",
            "error": {"code": "timeout", "message": "private text"}
            if status == "error"
            else None,
        }
    )
    final, _ = run(
        [lambda current: action(current), FinishDecision(kind="finish", reason="Done")],
        executor,
    )
    assert final["observations"][0]["status"] == status
    assert "private text" not in str(final["event_summaries"])


def test_tool_exception_becomes_error_observation():
    final, _ = run(
        [lambda current: action(current), FinishDecision(kind="finish", reason="Done")],
        FakeExecutor(RuntimeError("secret")),
    )
    assert final["observations"][0]["error_code"] == "tool_error"
    assert "secret" not in str(final)


def test_invalid_result_is_normalized_without_raw_content():
    final, _ = run(
        [lambda current: action(current), FinishDecision(kind="finish", reason="Done")],
        FakeExecutor({"status": "ok", "summary": "secret"}),
    )
    assert final["observations"][0]["error_code"] == "invalid_result"
    assert "secret" not in str(final)


def test_terminal_state_is_not_reexecuted_on_resume():
    final, executor = run([FinishDecision(kind="finish", reason="Done")])
    resumed, _ = run([], executor, current=final)
    assert resumed == final
    assert executor.calls == []


def test_step_and_tool_call_limits():
    final, executor = run(
        [
            lambda current: action(current),
            lambda current: action(current, "two", query="other"),
        ],
        current=state(max_steps=1),
    )
    assert final["terminal_reason"] == "step_limit"
    assert len(executor.calls) == 1

    final, executor = run(
        [
            lambda current: action(current),
            lambda current: action(current, "two", query="other"),
        ],
        current=state(max_tool_calls=1),
    )
    assert final["terminal_reason"] == "tool_call_limit"
    assert len(executor.calls) == 1
