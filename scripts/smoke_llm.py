import asyncio
import sys

import httpx

from ai_agent.application.services.llm_probe import run_llm_probe
from ai_agent.core.config import Settings
from ai_agent.llm.errors import LLMError
from ai_agent.llm.providers.llama_cpp import LlamaCppProvider

PROMPT = (
    "В payment-service наблюдаются HTTP 500 и PostgreSQL connection timeout. "
    "Какие данные нужно проверить для расследования? Используй только данное "
    "описание; не утверждай, что видел реальные логи, метрики или трассировки."
)


async def main() -> int:
    settings = Settings()
    try:
        async with httpx.AsyncClient(
            base_url=settings.llm_base_url.rstrip("/") + "/",
            timeout=settings.llm_connect_timeout_seconds,
        ) as client:
            response = await client.get("models")
            response.raise_for_status()
            models = response.json()["data"]
            if not isinstance(models, list) or not any(
                isinstance(model, dict) and model.get("id") == settings.llm_model
                for model in models
            ):
                print("Настроенная модель не найдена в /v1/models.", file=sys.stderr)
                return 1

        answer = await run_llm_probe(PROMPT, LlamaCppProvider(settings))
    except (httpx.HTTPError, LLMError, ValueError, KeyError, TypeError) as exc:
        print(
            f"Локальный llama-server недоступен или ответ некорректен: "
            f"{type(exc).__name__}",
            file=sys.stderr,
        )
        return 1

    print("Ответ локальной модели (без доступа к диагностическим данным):")
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
