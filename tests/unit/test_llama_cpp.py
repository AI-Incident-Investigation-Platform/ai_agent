import asyncio

import httpx

from ai_agent.core.config import Settings
from ai_agent.llm.providers.llama_cpp import LlamaCppProvider


def test_chat_uses_openai_compatible_endpoint():
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    settings = Settings(_env_file=None, llm_model="local-model")

    async def call_chat() -> str:
        async with httpx.AsyncClient(
            base_url="http://localhost:8080/v1/", transport=httpx.MockTransport(respond)
        ) as client:
            return await LlamaCppProvider(settings, client).chat(
                [{"role": "user", "content": "hello"}]
            )

    result = asyncio.run(call_chat())

    assert result == "ok"
    assert requests[0].url.path == "/v1/chat/completions"
    assert b'"model":"local-model"' in requests[0].content
