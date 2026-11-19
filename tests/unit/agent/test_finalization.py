import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker

from ai_agent.agent.finalization import build_finalization_graph, finalize_investigation
from ai_agent.application.contracts import StartAIRequest
from ai_agent.llm.types import ChatCompletion

CONTRACTS = Path(__file__).resolve().parents[3] / "docs/contracts"
NOW = datetime(2026, 10, 19, 14, 49, tzinfo=UTC)


def state(*, status="ready_for_finalization", supported=False):
    context = StartAIRequest.model_validate(
        json.loads((CONTRACTS / "examples/ai-start.request.json").read_text())
    )
    evidence = json.loads((CONTRACTS / "examples/ai-result.callback.json").read_text())[
        "evidence"
    ][0]
    evidence["hypothesis_ids"] = []
    hypothesis = json.loads(
        (CONTRACTS / "examples/ai-result.callback.json").read_text()
    )["hypotheses"][0]
    hypothesis["status"] = "supported" if supported else "pending"
    hypothesis["confidence"] = "medium" if supported else "low"
    evidence["hypothesis_ids"] = [hypothesis["id"]]
    return {
        "investigation_id": str(context.investigation_id),
        "context": context,
        "terminal_status": status,
        "terminal_reason": "agent_finished",
        "evidence": [evidence],
        "hypotheses": [hypothesis],
        "hypothesis_relations": {
            hypothesis["id"]: {"for": [evidence["id"]], "against": []}
        },
        "observations": [],
    }


class FakeLLM:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def chat(self, messages, *, tools=None):
        self.calls.append(messages)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return ChatCompletion(content=value)


def proposal(evidence_id, hypothesis_id=None):
    return json.dumps(
        {
            "symptom_evidence_ids": [evidence_id],
            "root_cause_hypothesis_id": hypothesis_id,
            "remediation": ["Проверить жизненный цикл соединений"],
            "prevention": ["Добавить тест утечки соединений"],
        }
    )


def finalize(current, model):
    return asyncio.run(finalize_investigation(current, model, finished_at=NOW))


def test_pending_hypothesis_produces_inconclusive_with_evidence_and_timeline():
    current = state()
    model = FakeLLM(proposal(current["evidence"][0]["id"]))
    result = finalize(current, model)
    assert result.status == "inconclusive"
    assert result.report.root_cause is None
    assert result.report.confidence == "low"
    assert result.report.evidence_ids == [UUID(current["evidence"][0]["id"])]
    assert len(result.timeline) == 1
    assert result.timeline[0].source.source_id == "es-log-123"
    assert result.timeline[0].occurred_at == current["context"].window.from_.replace(
        minute=35, second=8
    )
    assert result.timeline[0].causality == "observed"
    schema = json.loads(
        (CONTRACTS / "schemas/ai-result-callback.schema.json").read_text()
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        result.model_dump(mode="json")
    )


def test_supported_hypothesis_can_produce_completed_without_invented_claims():
    current = state(supported=True)
    evidence_id = current["evidence"][0]["id"]
    hypothesis_id = current["hypotheses"][0]["id"]
    result = finalize(current, FakeLLM(proposal(evidence_id, hypothesis_id)))
    assert result.status == "completed"
    assert result.report.root_cause == current["hypotheses"][0]["title"]
    assert result.report.root_cause_service_ids == [
        UUID(current["evidence"][0]["service_ids"][0])
    ]
    assert result.report.symptoms == [current["evidence"][0]["summary"]]
    assert result.report.causal_chain == []
    schema = json.loads(
        (CONTRACTS / "schemas/ai-result-callback.schema.json").read_text()
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        result.model_dump(mode="json")
    )


def test_unknown_source_is_retried_once_and_falls_back_to_inconclusive():
    current = state(supported=True)
    invented = "99999999-9999-4999-8999-999999999998"
    model = FakeLLM(proposal(invented), proposal(invented))
    result = finalize(current, model)
    assert len(model.calls) == 2
    assert result.status == "inconclusive"
    assert result.report.root_cause is None
    assert result.report.symptoms == []


def test_invalid_json_has_bounded_repair_and_safe_fallback():
    current = state()
    model = FakeLLM("not json", "still not json")
    result = finalize(current, model)
    assert len(model.calls) == 2
    assert result.status == "inconclusive"
    assert result.report is not None


def test_unavailable_model_and_missing_optional_fields_have_safe_results():
    current = state()
    failed = FakeLLM(TimeoutError("model unavailable"), TimeoutError("again"))
    result = finalize(current, failed)
    assert result.status == "inconclusive"
    assert len(failed.calls) == 2
    minimal = FakeLLM(json.dumps({"symptom_evidence_ids": []}))
    assert finalize(current, minimal).report.remediation == []


def test_no_evidence_never_calls_model_and_returns_inconclusive():
    current = state()
    current["evidence"] = []
    current["hypotheses"] = []
    model = FakeLLM()
    result = finalize(current, model)
    assert result.status == "inconclusive"
    assert result.report.root_cause is None
    assert model.calls == []


def test_failed_canceled_and_timed_out_preserve_partial_evidence_without_report():
    for status in ("failed", "canceled", "timed_out"):
        current = state(status=status)
        result = finalize(current, FakeLLM())
        assert result.status == status
        assert result.report is None
        assert len(result.evidence) == 1
        assert result.error is not None


def test_opposing_or_partial_evidence_prevents_completed():
    current = state(supported=True)
    evidence_id = current["evidence"][0]["id"]
    hypothesis_id = current["hypotheses"][0]["id"]
    current["hypothesis_relations"][hypothesis_id]["against"] = [evidence_id]
    assert finalize(current, FakeLLM(proposal(evidence_id, hypothesis_id))).status == (
        "inconclusive"
    )
    current["hypothesis_relations"][hypothesis_id]["against"] = []
    current["evidence"][0]["confidence_note"] = "Источник вернул неполные данные"
    assert finalize(current, FakeLLM(proposal(evidence_id, hypothesis_id))).status == (
        "inconclusive"
    )


def test_foreign_or_unsafe_evidence_cannot_support_report():
    for change in (
        lambda item: item["source"].update(
            metadata={"environment_id": "99999999-9999-4999-8999-999999999999"}
        ),
        lambda item: item["source"].update(url="http://untrusted.example/log"),
        lambda item: item["source"].update(
            url="https://trusted.example/log#token=private"
        ),
        lambda item: item["source"].update(observed_at="2026-10-19T15:00:00Z"),
        lambda item: item.update(service_ids=["99999999-9999-4999-8999-999999999999"]),
    ):
        current = state(supported=True)
        change(current["evidence"][0])
        result = finalize(current, FakeLLM())
        assert result.status == "inconclusive"
        assert result.evidence == []
        assert result.report.root_cause is None


def test_missing_reciprocal_hypothesis_link_blocks_root_cause():
    current = state(supported=True)
    evidence_id = current["evidence"][0]["id"]
    hypothesis_id = current["hypotheses"][0]["id"]
    current["evidence"][0]["hypothesis_ids"] = []
    result = finalize(current, FakeLLM(proposal(evidence_id, hypothesis_id)))
    assert result.status == "inconclusive"
    assert result.hypotheses == []


def test_four_hypotheses_are_not_silently_truncated():
    current = state(supported=True)
    current["hypotheses"] = current["hypotheses"] * 4
    result = finalize(current, FakeLLM(proposal(current["evidence"][0]["id"])))
    assert result.status == "inconclusive"
    assert result.hypotheses == []


def test_invalid_internal_relation_falls_back_to_inconclusive():
    current = state(supported=True)
    evidence_id = current["evidence"][0]["id"]
    hypothesis_id = current["hypotheses"][0]["id"]
    current["hypothesis_relations"][hypothesis_id]["for"] = ["not-a-uuid"]
    result = finalize(current, FakeLLM(proposal(evidence_id, hypothesis_id)))
    assert result.status == "inconclusive"
    assert result.report.root_cause is None


def test_report_redacts_secret_and_email_in_evidence_and_recommendation():
    current = state()
    evidence_id = current["evidence"][0]["id"]
    current["evidence"][0]["summary"] = "token=private user@example.com"
    response = json.loads(proposal(evidence_id))
    response["remediation"] = ["Проверить token=private user@example.com"]
    result = finalize(current, FakeLLM(json.dumps(response)))
    assert "private" not in str(result)
    assert "user@example.com" not in str(result)


def test_timeline_uses_only_source_times_and_is_sorted():
    current = state()
    second = json.loads(json.dumps(current["evidence"][0]))
    second["id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaab"
    second["source"]["source_id"] = "es-log-124"
    second["source"]["observed_at"] = "2026-10-19T14:10:00Z"
    third = json.loads(json.dumps(second))
    third["id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaac"
    third["source"]["source_id"] = "es-log-125"
    third["source"]["observed_at"] = None
    current["evidence"].extend([second, third])
    result = finalize(current, FakeLLM(proposal(current["evidence"][0]["id"])))
    assert [item.source.source_id for item in result.timeline] == [
        "es-log-124",
        "es-log-123",
    ]


def test_finalization_graph_returns_callback_and_is_deterministic():
    current = state()
    evidence_id = current["evidence"][0]["id"]
    graph = build_finalization_graph(FakeLLM(proposal(evidence_id)), finished_at=NOW)
    output = asyncio.run(graph.ainvoke(current))
    assert output["result_callback"]["status"] == "inconclusive"
    first = finalize(current, FakeLLM(proposal(evidence_id)))
    second = finalize(current, FakeLLM(proposal(evidence_id)))
    assert first == second
