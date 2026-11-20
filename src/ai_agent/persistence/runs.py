import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import UUID

from psycopg.types.json import Jsonb

from ai_agent.application.contracts import AIResultCallback, StartAIRequest
from ai_agent.core.config import Settings
from ai_agent.persistence.checkpoints import connect_storage

_ADMISSION_LOCK = 72465311
_WORKER_LOCK = 72465312


class RunBusy(Exception):
    pass


class RunConflict(Exception):
    pass


async def migrate_runs(settings: Settings) -> None:
    async with connect_storage(settings) as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_ADMISSION_LOCK,))
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_runs (
                id uuid PRIMARY KEY,
                request_key text UNIQUE NOT NULL,
                request_hash text NOT NULL,
                request jsonb NOT NULL,
                status text NOT NULL CHECK (status IN (
                    'pending', 'running', 'completed', 'inconclusive',
                    'failed', 'canceled', 'timed_out'
                )),
                accepted_at timestamptz NOT NULL,
                deadline_at timestamptz NOT NULL,
                started_at timestamptz,
                cancel_requested boolean NOT NULL DEFAULT false,
                finished_at timestamptz,
                result jsonb,
                next_delivery_at timestamptz,
                delivery_attempts integer NOT NULL DEFAULT 0,
                delivered_at timestamptz
            )
        """)
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ai_runs_single_active
            ON ai_runs ((true)) WHERE status IN ('pending', 'running')
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ai_runs_delivery
            ON ai_runs (next_delivery_at) WHERE delivered_at IS NULL
                AND next_delivery_at IS NOT NULL
        """)


class RunRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def register(self, request: StartAIRequest, key: str) -> dict:
        body = request.model_dump(mode="json", by_alias=True)
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        async with connect_storage(self.settings) as conn, conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_ADMISSION_LOCK,))
            cursor = await conn.execute(
                "SELECT * FROM ai_runs WHERE id = %s OR request_key = %s",
                (request.investigation_id, key),
            )
            matches = await cursor.fetchall()
            if matches:
                row = matches[0]
                if (
                    len(matches) != 1
                    or row["id"] != request.investigation_id
                    or row["request_hash"] != digest
                    or row["request_key"] != key
                ):
                    raise RunConflict
                return row
            cursor = await conn.execute(
                "SELECT 1 FROM ai_runs WHERE status IN ('pending', 'running')"
            )
            if await cursor.fetchone():
                raise RunBusy
            cursor = await conn.execute(
                """INSERT INTO ai_runs
                   (id, request_key, request_hash, request, status,
                    accepted_at, deadline_at)
                   VALUES (%s, %s, %s, %s, 'pending', now(),
                           now() + %s) RETURNING *""",
                (
                    request.investigation_id,
                    key,
                    digest,
                    Jsonb(body),
                    timedelta(seconds=request.budget.timeout_seconds),
                ),
            )
            return await cursor.fetchone()

    async def read(self, run_id: UUID) -> dict | None:
        async with connect_storage(self.settings) as conn:
            cursor = await conn.execute(
                "SELECT * FROM ai_runs WHERE id = %s", (run_id,)
            )
            return await cursor.fetchone()

    async def request_cancel(self, run_id: UUID) -> dict | None:
        async with connect_storage(self.settings) as conn:
            cursor = await conn.execute(
                """UPDATE ai_runs
                   SET cancel_requested = cancel_requested
                       OR status IN ('pending', 'running')
                   WHERE id = %s RETURNING *""",
                (run_id,),
            )
            return await cursor.fetchone()

    @asynccontextmanager
    async def worker_session(self) -> AsyncIterator[object | None]:
        async with connect_storage(self.settings) as conn:
            cursor = await conn.execute(
                "SELECT pg_try_advisory_lock(%s) AS acquired", (_WORKER_LOCK,)
            )
            row = await cursor.fetchone()
            yield conn if row["acquired"] else None

    async def claim(self, conn) -> tuple[dict | None, bool]:
        async with conn.transaction():
            cursor = await conn.execute(
                """SELECT * FROM ai_runs WHERE status IN ('pending', 'running')
                   FOR UPDATE"""
            )
            row = await cursor.fetchone()
            if row is None or row["status"] == "running":
                return row, row is not None
            cursor = await conn.execute(
                """UPDATE ai_runs SET status = 'running', started_at = now()
                   WHERE id = %s RETURNING *""",
                (row["id"],),
            )
            return await cursor.fetchone(), False

    async def finish(self, conn, result: AIResultCallback) -> bool:
        cursor = await conn.execute(
            """UPDATE ai_runs SET status = %s, finished_at = %s, result = %s,
                      next_delivery_at = now()
               WHERE id = %s AND status = 'running'
                 AND (NOT cancel_requested OR %s = 'canceled')
               RETURNING id""",
            (
                result.status,
                result.finished_at,
                Jsonb(result.model_dump(mode="json")),
                result.investigation_id,
                result.status,
            ),
        )
        return await cursor.fetchone() is not None

    async def due_result(self, conn) -> dict | None:
        cursor = await conn.execute(
            """SELECT id, result, delivery_attempts FROM ai_runs
               WHERE delivered_at IS NULL AND next_delivery_at <= now()
               ORDER BY next_delivery_at LIMIT 1"""
        )
        return await cursor.fetchone()

    async def record_delivery(self, conn, row: dict, delivered: bool) -> None:
        if delivered:
            await conn.execute(
                "UPDATE ai_runs SET delivered_at = now() WHERE id = %s", (row["id"],)
            )
        else:
            delay = timedelta(seconds=min(300, 2 ** min(row["delivery_attempts"], 9)))
            await conn.execute(
                """UPDATE ai_runs SET delivery_attempts = delivery_attempts + 1,
                          next_delivery_at = now() + %s WHERE id = %s""",
                (delay, row["id"]),
            )
