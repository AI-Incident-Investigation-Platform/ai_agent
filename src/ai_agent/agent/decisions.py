from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ai_agent.agent.state import InvestigationState


class ActionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["action"]
    tool_call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, object]


class FinishDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["finish"]
    reason: str = Field(min_length=1, max_length=500)


class DecisionProvider(Protocol):
    async def decide(self, state: InvestigationState) -> object: ...


class ToolExecutor(Protocol):
    async def execute(self, name: str, arguments: dict[str, object]) -> object: ...
