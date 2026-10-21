from collections.abc import Sequence

import httpx

from ai_agent.core.config import Settings


class LlamaCppProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._client = client

    async def chat(self, messages: Sequence[dict[str, str]]) -> str:
        async def request(client: httpx.AsyncClient) -> str:
            response = await client.post(
                "chat/completions",
                json={"model": self._settings.llm_model, "messages": list(messages)},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        if self._client is not None:
            return await request(self._client)
        async with httpx.AsyncClient(
            base_url=self._settings.llm_base_url.rstrip("/") + "/",
            timeout=self._settings.llm_timeout_seconds,
        ) as client:
            return await request(client)
