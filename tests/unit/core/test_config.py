from ai_agent.core.config import Settings


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("AI_AGENT_LLM_MODEL", "local-model")
    assert Settings(_env_file=None).llm_model == "local-model"
