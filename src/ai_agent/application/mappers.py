from ai_agent.agent.state import InvestigationState
from ai_agent.application.contracts import StartAIRequest
from ai_agent.domain.models import InvestigationContext


def to_graph_state(request: StartAIRequest) -> InvestigationState:
    context = InvestigationContext.model_validate(
        request.model_dump(exclude={"schema_version"})
    )
    return {"investigation_id": str(request.investigation_id), "context": context}


def start_from_graph_state(state: InvestigationState) -> StartAIRequest:
    context = state.get("context")
    if context is None or str(context.investigation_id) != state["investigation_id"]:
        raise ValueError("Graph state has no matching investigation context")
    return StartAIRequest.model_validate(
        {"schema_version": "1.0", **context.model_dump(by_alias=True)}
    )
