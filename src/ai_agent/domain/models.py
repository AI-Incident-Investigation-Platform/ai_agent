from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AnyUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


def _require_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be UTC")
    return value


UTCTimestamp = Annotated[AwareDatetime, AfterValidator(_require_utc)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExecutionBudget(ContractModel):
    max_steps: int = Field(ge=1, le=20, strict=True)
    max_tool_calls: int = Field(ge=1, le=40, strict=True)
    timeout_seconds: int = Field(ge=1, le=1200, strict=True)


class TimeWindow(ContractModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: UTCTimestamp = Field(alias="from")
    to: UTCTimestamp

    @model_validator(mode="after")
    def require_ordered_window(self) -> TimeWindow:
        if self.from_ > self.to:
            raise ValueError("Time window start must not exceed end")
        return self


class InvestigationContext(ContractModel):
    investigation_id: UUID
    incident_id: UUID
    project_id: UUID
    environment_id: UUID
    service_ids: list[UUID]
    detected_at: UTCTimestamp
    window: TimeWindow
    alert_summary: str
    budget: ExecutionBudget
    attempt: int = Field(ge=1, strict=True)
    parent_investigation_id: UUID | None


class SourceLink(ContractModel):
    source_type: Literal[
        "elasticsearch",
        "prometheus",
        "tempo",
        "github",
        "docker",
        "deployment",
        "healthcheck",
        "manual",
        "docs_rag",
        "incident_memory",
    ]
    source_id: str | None = None
    url: AnyUrl | None = None
    observed_at: UTCTimestamp | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class Evidence(ContractModel):
    id: UUID
    investigation_id: UUID
    source: SourceLink
    title: str
    summary: str
    excerpt: str | None = None
    service_ids: list[UUID]
    hypothesis_ids: list[UUID]
    collected_at: UTCTimestamp
    confidence_note: str | None = None


class Hypothesis(ContractModel):
    id: UUID
    investigation_id: UUID
    title: str
    explanation: str
    status: Literal["pending", "supported", "rejected"]
    confidence: Literal["high", "medium", "low"]
    evidence_ids: list[UUID]
    updated_at: UTCTimestamp


class TimelineEntry(ContractModel):
    id: UUID
    incident_id: UUID
    investigation_id: UUID | None = None
    occurred_at: UTCTimestamp
    event_type: str
    title: str
    description: str
    service_ids: list[UUID]
    source: SourceLink
    causality: Literal["observed", "correlated", "supported_cause", "unknown"]


class RCAReport(ContractModel):
    id: UUID
    incident_id: UUID
    investigation_id: UUID
    outcome: Literal["completed", "inconclusive"]
    summary: str
    symptoms: list[str]
    root_cause: str | None
    root_cause_service_ids: list[UUID]
    causal_chain: list[str]
    hypothesis_ids: list[UUID]
    evidence_ids: list[UUID]
    timeline_entry_ids: list[UUID]
    confidence: Literal["high", "medium", "low"]
    remediation: list[str]
    prevention: list[str]
    limitations: list[str]
    generated_at: UTCTimestamp


class Investigation(ContractModel):
    id: UUID
    incident_id: UUID
    project_id: UUID
    environment_id: UUID
    status: Literal[
        "pending",
        "running",
        "completed",
        "inconclusive",
        "failed",
        "timed_out",
        "canceled",
    ]
    created_at: UTCTimestamp
    started_at: UTCTimestamp | None = None
    finished_at: UTCTimestamp | None = None
    attempt: int = Field(ge=1, strict=True)
    parent_investigation_id: UUID | None = None
    current_step: int = Field(ge=0, strict=True)
    tool_calls_count: int = Field(ge=0, strict=True)
    budget: ExecutionBudget
    failure_code: str | None = None
    failure_message: str | None = None
