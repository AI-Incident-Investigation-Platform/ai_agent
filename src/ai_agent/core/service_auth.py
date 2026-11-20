import asyncio

import httpx
import jwt
from fastapi import HTTPException


class IncidentsAuthorization:
    def __init__(self, auth_url: str):
        self.keys = jwt.PyJWKClient(
            f"{auth_url.rstrip('/')}/.well-known/jwks.json", timeout=3
        )

    async def __call__(self, authorization: str | None, action: str) -> None:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 8192:
            raise HTTPException(401, "Service token required")
        try:
            key = await asyncio.to_thread(self.keys.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience="ai-backend",
                issuer="auth",
                options={"require": ["iss", "aud", "sub", "iat", "exp", "jti"]},
            )
        except jwt.PyJWKClientConnectionError:
            raise HTTPException(503, "Service authorization unavailable") from None
        except jwt.PyJWTError:
            raise HTTPException(401, "Invalid service token") from None
        if claims.get("token_use") != "service" or "sid" in claims:
            raise HTTPException(401, "Invalid service token")
        if (
            claims["sub"] != "incidents"
            or f"ai.investigations.{action}" not in str(claims.get("scope", "")).split()
        ):
            raise HTTPException(403, "Service permission denied")


class ResultDelivery:
    def __init__(self, auth_url: str, incidents_url: str, secret: str):
        self.token_url = f"{auth_url.rstrip('/')}/internal/v1/oauth/token"
        self.result_url = f"{incidents_url.rstrip('/')}/internal/v1/ai/results"
        self.credentials = httpx.BasicAuth("ai-backend", secret)

    async def __call__(self, result: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
                token = await client.post(
                    self.token_url,
                    auth=self.credentials,
                    data={
                        "grant_type": "client_credentials",
                        "audience": "main-ai-sink",
                        "scope": "incidents.ai.results",
                    },
                )
                token.raise_for_status()
                response = await client.post(
                    self.result_url,
                    json=result,
                    headers={"Authorization": f"Bearer {token.json()['access_token']}"},
                )
                if response.status_code != 202:
                    return False
                ack = response.json()
                return ack.get("accepted") is True or ack.get("deduplicated") is True
        except httpx.HTTPError, ValueError, KeyError, AttributeError, TypeError:
            return False
