from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_AGENT_", env_file=".env")

    log_level: str = "INFO"
    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_model: str = "Qwen2.5-Coder-7B-Instruct"
    llm_timeout_seconds: float = Field(default=60, gt=0)
