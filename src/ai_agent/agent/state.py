from typing import NotRequired, TypedDict


class InvestigationState(TypedDict):
    investigation_id: str


class LLMProbeState(TypedDict):
    prompt: str
    response: NotRequired[str]
