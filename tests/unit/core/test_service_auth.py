import asyncio
from time import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from ai_agent.core.service_auth import IncidentsAuthorization


def test_accepts_only_incidents_service_token_with_correct_audience_and_scope():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = IncidentsAuthorization("http://auth")
    verifier.keys = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private_key.public_key())
    )
    claims = {
        "iss": "auth",
        "aud": "ai-backend",
        "sub": "incidents",
        "iat": int(time()),
        "exp": int(time()) + 60,
        "jti": "test",
        "token_use": "service",
        "scope": "ai.investigations.start",
    }

    def check(action, **overrides):
        token = jwt.encode({**claims, **overrides}, private_key, algorithm="RS256")
        asyncio.run(verifier(f"Bearer {token}", action))

    check("start")
    for action, status, overrides in (
        ("cancel", 403, {}),
        ("start", 403, {"sub": "other-service"}),
        ("start", 401, {"aud": "other-service"}),
        ("start", 401, {"token_use": "user"}),
    ):
        with pytest.raises(HTTPException) as error:
            check(action, **overrides)
        assert error.value.status_code == status


def test_result_delivery_accepts_backend_duplicate_ack(monkeypatch):
    import httpx

    from ai_agent.core.service_auth import ResultDelivery

    def handler(request):
        if request.url.host == "auth":
            assert request.method == "POST"
            assert request.url.path == "/internal/v1/oauth/token"
            assert request.headers["Authorization"].startswith("Basic ")
            assert b"audience=main-ai-sink" in request.content
            assert b"scope=incidents.ai.results" in request.content
            return httpx.Response(200, json={"access_token": "test-token"})
        assert request.url.path == "/internal/v1/ai/results"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert b"same-event" in request.content
        return httpx.Response(202, json={"accepted": False, "deduplicated": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: client)
    delivery = ResultDelivery("http://auth", "http://incidents", "test-secret")
    assert asyncio.run(delivery({"event_id": "same-event"}))
