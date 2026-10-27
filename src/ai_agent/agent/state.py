from typing import NotRequired, TypedDict

from ai_agent.domain.models import InvestigationContext


class InvestigationState(TypedDict):
    investigation_id: str
    context: NotRequired[InvestigationContext]


class LLMProbeState(TypedDict):
    prompt: str
    response: NotRequired[str]
