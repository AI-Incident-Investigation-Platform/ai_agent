import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from time import time
from typing import Literal

from ai_agent.agent.state import InvestigationState


class RunStopped(Exception):
    def __init__(self, status: Literal["canceled", "timed_out"]):
        super().__init__(status)
        self.status = status

    def state_update(self) -> dict[str, object]:
        return {
            "terminal_status": self.status,
            "terminal_reason": (
                "cancel_requested" if self.status == "canceled" else "deadline_exceeded"
            ),
            "pending_action": None,
            "validated_action": None,
        }


class ExecutionControl:
    def __init__(
        self,
        is_cancel_requested: Callable[[str], bool] | None = None,
        clock: Callable[[], float] = time,
    ):
        self.is_cancel_requested = is_cancel_requested
        self.clock = clock

    def check(self, state: InvestigationState) -> float | None:
        deadline = state.get("deadline_at")
        remaining = None if deadline is None else deadline - self.clock()
        if remaining is not None and remaining <= 0:
            raise RunStopped("timed_out")
        if self.is_cancel_requested and self.is_cancel_requested(
            state["investigation_id"]
        ):
            raise RunStopped("canceled")
        return remaining

    @asynccontextmanager
    async def bounded(self, state: InvestigationState) -> AsyncIterator[None]:
        timer = asyncio.timeout(self.check(state))
        try:
            async with timer:
                yield
        except TimeoutError as exc:
            if timer.expired():
                raise RunStopped("timed_out") from exc
            raise
        if timer.expired():
            raise RunStopped("timed_out")
