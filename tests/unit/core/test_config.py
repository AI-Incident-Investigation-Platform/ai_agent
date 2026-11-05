from ai_agent.core.config import Settings


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("AI_AGENT_LLM_MODEL", "local-model")
    assert Settings(_env_file=None).llm_model == "local-model"


def test_mcp_settings_read_environment_and_hide_token(monkeypatch):
    monkeypatch.setenv("AI_AGENT_MCP_URL", "https://mcp.example.test/mcp")
    monkeypatch.setenv("AI_AGENT_MCP_TOKEN", "secret-token")
    settings = Settings(_env_file=None)
    assert str(settings.mcp_url) == "https://mcp.example.test/mcp"
    assert settings.mcp_token.get_secret_value() == "secret-token"
    assert "secret-token" not in repr(settings)
