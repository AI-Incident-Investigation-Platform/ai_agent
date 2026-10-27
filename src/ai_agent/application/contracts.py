from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from ai_agent.domain.models import (
    ContractModel,
    Evidence,
    ExecutionBudget,
    Hypothesis,
    InvestigationContext,
    RCAReport,
    TimelineEntry,
    UTCTimestamp,
)


class StartAIRequest(InvestigationContext):
    schema_version: Literal["1.0"]


class ErrorDetail(ContractModel):
    field: str
    message: str


class Problem(ContractModel):
    type: str
    title: str
    status: int = Field(strict=True)
    code: str
    detail: str
    request_id: str
    errors: list[ErrorDetail] = Field(default_factory=list)


class _PendingData(ContractModel):
    reason: str


class _StartedData(ContractModel):
    model: str
    budget: ExecutionBudget


class _ProgressData(ContractModel):
    step: int = Field(strict=True)
    tool_calls_count: int = Field(strict=True)
    summary: str


class _ToolStartedData(ContractModel):
    tool_call_id: UUID
    tool_name: str
    input_summary: str


class _ToolCompletedData(ContractModel):
    tool_call_id: UUID
    tool_name: str
    output_summary: str
    duration_ms: int = Field(ge=0, strict=True)


class _ToolFailedData(ContractModel):
    tool_call_id: UUID
    tool_name: str
    error_code: str
    message: str


class _HypothesisUpdatedData(ContractModel):
    hypothesis: Hypothesis


class _EvidenceAddedData(ContractModel):
    evidence: Evidence


class _CompletedData(ContractModel):
    result_event_id: UUID


class _InconclusiveData(ContractModel):
    reason: str
    result_event_id: UUID


class _FailedData(ContractModel):
    error_code: str
    message: str


class _TimedOutData(ContractModel):
    limit_seconds: int = Field(strict=True)


class _CanceledData(ContractModel):
    requested_by: str | None = None


EVENT_DATA_MODELS: dict[str, type[ContractModel]] = {
    "investigation.pending": _PendingData,
    "investigation.started": _StartedData,
    "investigation.progress": _ProgressData,
    "tool.started": _ToolStartedData,
    "tool.completed": _ToolCompletedData,
    "tool.failed": _ToolFailedData,
    "hypothesis.updated": _HypothesisUpdatedData,
    "evidence.added": _EvidenceAddedData,
    "investigation.completed": _CompletedData,
    "investigation.inconclusive": _InconclusiveData,
    "investigation.failed": _FailedData,
    "investigation.timed_out": _TimedOutData,
    "investigation.canceled": _CanceledData,
}


class InvestigationEvent(ContractModel):
    schema_version: Literal["1.0"]
    event_id: UUID
    investigation_id: UUID
    incident_id: UUID
    sequence: int = Field(ge=1, strict=True)
    type: Literal[
        "investigation.pending",
        "investigation.started",
        "investigation.progress",
        "tool.started",
        "tool.completed",
        "tool.failed",
        "hypothesis.updated",
        "evidence.added",
        "investigation.completed",
        "investigation.inconclusive",
        "investigation.failed",
        "investigation.timed_out",
        "investigation.canceled",
    ]
    occurred_at: UTCTimestamp
    data: dict[str, object]

    @model_validator(mode="after")
    def validate_event_data(self) -> InvestigationEvent:
        EVENT_DATA_MODELS[self.type].model_validate(self.data)
        return self


class AIResultCallback(ContractModel):
    schema_version: Literal["1.0"]
    event_id: UUID
    investigation_id: UUID
    incident_id: UUID
    status: Literal["completed", "inconclusive", "failed", "timed_out", "canceled"]
    finished_at: UTCTimestamp
    report: RCAReport | None
    hypotheses: list[Hypothesis] = Field(max_length=3)
    evidence: list[Evidence]
    timeline: list[TimelineEntry]
    error: str | None = None

    @model_validator(mode="after")
    def validate_report(self) -> AIResultCallback:
        if self.status in {"completed", "inconclusive"}:
            if self.report is None or self.report.outcome != self.status:
                raise ValueError("Completed/inconclusive result needs matching report")
        if self.report and (
            self.report.investigation_id != self.investigation_id
            or self.report.incident_id != self.incident_id
        ):
            raise ValueError("Report IDs must match callback IDs")
        if any(
            item.investigation_id != self.investigation_id for item in self.hypotheses
        ):
            raise ValueError("Hypothesis must belong to callback investigation")
        if any(
            item.investigation_id != self.investigation_id for item in self.evidence
        ):
            raise ValueError("Evidence must belong to callback investigation")
        if any(
            item.incident_id != self.incident_id
            or item.investigation_id not in {None, self.investigation_id}
            for item in self.timeline
        ):
            raise ValueError("Timeline must belong to callback scope")
        return self
