import asyncio
import os

import pytest

from ai_agent.application.services.llm_probe import run_llm_probe
from ai_agent.core.config import Settings
from ai_agent.llm.providers.llama_cpp import LlamaCppProvider

pytestmark = pytest.mark.skipif(
    os.getenv("AI_AGENT_RUN_LIVE_LLM") != "1",
    reason="Set AI_AGENT_RUN_LIVE_LLM=1 to test the local model",
)


def test_local_qwen_through_langgraph():
    result = asyncio.run(
        run_llm_probe(
            "Reply with exactly the word READY.",
            LlamaCppProvider(Settings()),
        )
    )
    assert result.strip() == "READY"
