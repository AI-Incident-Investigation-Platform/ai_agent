from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from ai_agent.application.contracts import StartAIRequest
from ai_agent.core.config import Settings
from ai_agent.core.service_auth import IncidentsAuthorization
from ai_agent.persistence.checkpoints import CheckpointStorageError
from ai_agent.persistence.runs import RunBusy, RunConflict, RunRegistry

Authorize = Callable[[str | None, str], Awaitable[None]]
Authorization = Annotated[str | None, Header()]
IdempotencyKey = Annotated[str, Header(min_length=1, max_length=200)]


def build_router(settings: Settings, authorize: Authorize | None = None) -> APIRouter:
    router = APIRouter(prefix="/internal/v1/investigations")
    registry = RunRegistry(settings)
    if authorize is None and settings.auth_url is not None:
        authorize = IncidentsAuthorization(str(settings.auth_url))

    async def check(authorization: str | None, action: str) -> None:
        if authorize is None:
            raise HTTPException(503, "Service authorization is not configured")
        await authorize(authorization, action)

    @router.post("", status_code=202)
    async def start(
        body: StartAIRequest,
        idempotency_key: IdempotencyKey,
        authorization: Authorization = None,
    ):
        await check(authorization, "start")
        try:
            row = await registry.register(body, idempotency_key)
        except RunBusy:
            raise HTTPException(
                429, "AI executor busy", headers={"Retry-After": "5"}
            ) from None
        except RunConflict:
            raise HTTPException(409, "Start conflicts with an existing run") from None
        except CheckpointStorageError:
            raise HTTPException(503, "Run registry unavailable") from None
        return {
            "investigation_id": row["id"],
            "status": "pending" if row["started_at"] is None else "running",
            "accepted_at": row["accepted_at"],
        }

    @router.get("/{investigation_id}")
    async def status(investigation_id: UUID, authorization: Authorization = None):
        await check(authorization, "readback")
        try:
            row = await registry.read(investigation_id)
        except CheckpointStorageError:
            raise HTTPException(503, "Run registry unavailable") from None
        if row is None:
            raise HTTPException(404, "Investigation not found")
        return {
            "id": row["id"],
            "status": row["status"],
            "cancel_requested": row["cancel_requested"],
        }

    @router.post("/{investigation_id}/cancel", status_code=202)
    async def cancel(investigation_id: UUID, authorization: Authorization = None):
        await check(authorization, "cancel")
        try:
            row = await registry.request_cancel(investigation_id)
        except CheckpointStorageError:
            raise HTTPException(503, "Run registry unavailable") from None
        if row is None:
            raise HTTPException(404, "Investigation not found")
        return {"investigation_id": row["id"], "status": row["status"]}

    @router.get("/{investigation_id}/result")
    async def result(investigation_id: UUID, authorization: Authorization = None):
        await check(authorization, "readback")
        try:
            row = await registry.read(investigation_id)
        except CheckpointStorageError:
            raise HTTPException(503, "Run registry unavailable") from None
        if row is None:
            raise HTTPException(404, "Investigation not found")
        if row["result"] is None:
            raise HTTPException(409, "Investigation is still running")
        return row["result"]

    return router
