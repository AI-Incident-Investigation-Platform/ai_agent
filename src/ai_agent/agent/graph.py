from langgraph.graph import END, START, StateGraph

from ai_agent.agent.state import InvestigationState, LLMProbeState
from ai_agent.llm.errors import LLMResponseError
from ai_agent.llm.types import ChatMessage, ChatProvider


def build_graph():
    graph = StateGraph(InvestigationState)
    graph.add_edge(START, END)
    return graph.compile()


def build_llm_probe_graph(provider: ChatProvider):
    """Compile a one-shot LLM probe; not an incident investigation graph."""

    async def call_model(state: LLMProbeState) -> dict[str, str]:
        completion = await provider.chat([ChatMessage("user", state["prompt"])])
        if completion.tool_calls:
            raise LLMResponseError("Tool calls are not supported by the probe graph")
        if not completion.content:
            raise LLMResponseError("Local inference returned no text")
        return {"response": completion.content}

    graph = StateGraph(LLMProbeState)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "call_model")
    graph.add_edge("call_model", END)
    return graph.compile()
