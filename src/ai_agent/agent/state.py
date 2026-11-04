from typing import Literal, NotRequired, TypedDict

from ai_agent.domain.models import ExecutionBudget, InvestigationContext


class Observation(TypedDict):
    tool_call_id: str
    tool_name: str
    status: Literal["ok", "empty", "partial", "error"]
    summary: str
    source_refs: list[dict[str, object]]
    truncated: bool
    error_code: str | None


class InvestigationState(TypedDict):
    investigation_id: str
    context: NotRequired[InvestigationContext]
    budget: NotRequired[ExecutionBudget]
    step: NotRequired[int]
    tool_calls_count: NotRequired[int]
    action_history: NotRequired[list[str]]
    observations: NotRequired[list[Observation]]
    evidence: NotRequired[list[dict[str, object]]]
    event_summaries: NotRequired[list[str]]
    pending_action: NotRequired[dict[str, object] | None]
    validated_action: NotRequired[dict[str, object] | None]
    terminal_status: NotRequired[
        Literal["ready_for_finalization", "inconclusive"] | None
    ]
    terminal_reason: NotRequired[str | None]


class LLMProbeState(TypedDict):
    prompt: str
    response: NotRequired[str]
