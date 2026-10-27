from enum import StrEnum
from uuid import UUID


class InvestigationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELED = "canceled"


TERMINAL = frozenset(
    {
        InvestigationStatus.COMPLETED,
        InvestigationStatus.INCONCLUSIVE,
        InvestigationStatus.FAILED,
        InvestigationStatus.TIMED_OUT,
        InvestigationStatus.CANCELED,
    }
)


def transition_status(
    current: InvestigationStatus, target: InvestigationStatus
) -> InvestigationStatus:
    if current == target:
        return current
    if current == InvestigationStatus.PENDING and target in {
        InvestigationStatus.RUNNING,
        InvestigationStatus.CANCELED,
    }:
        return target
    if current == InvestigationStatus.RUNNING and target in TERMINAL:
        return target
    raise ValueError(f"Illegal investigation transition: {current} -> {target}")


def require_new_retry(
    previous_id: UUID,
    previous_attempt: int,
    new_id: UUID,
    new_attempt: int,
    parent_id: UUID | None,
) -> None:
    if (
        new_id == previous_id
        or new_attempt != previous_attempt + 1
        or parent_id != previous_id
    ):
        raise ValueError("Retry requires a new ID, next attempt and previous parent")
