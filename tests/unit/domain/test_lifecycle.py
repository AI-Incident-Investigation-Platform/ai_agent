from uuid import UUID

import pytest

from ai_agent.domain.lifecycle import (
    InvestigationStatus,
    require_new_retry,
    transition_status,
)


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
