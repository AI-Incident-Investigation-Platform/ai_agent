from ai_agent.agent.graph import build_llm_probe_graph
from ai_agent.llm.types import ChatProvider


async def run_llm_probe(prompt: str, provider: ChatProvider) -> str:
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt must not be empty")
    state = await build_llm_probe_graph(provider).ainvoke({"prompt": prompt})
    return state["response"]
