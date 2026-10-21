from langgraph.graph import END, START, StateGraph

from ai_agent.agent.state import InvestigationState


def build_graph():
    graph = StateGraph(InvestigationState)
    graph.add_edge(START, END)
    return graph.compile()
