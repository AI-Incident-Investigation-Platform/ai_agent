from ai_agent.agent.graph import build_graph


def test_graph_compiles_and_preserves_initial_state():
    state = {"investigation_id": "inv-1"}
    assert build_graph().invoke(state) == state
