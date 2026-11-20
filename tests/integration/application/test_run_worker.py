import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from psycopg import AsyncConnection, sql

from ai_agent.api.app import create_app
from ai_agent.application.services.run_worker import RunWorker
from ai_agent.core.config import Settings
from ai_agent.llm.types import ChatCompletion, ToolCall
from ai_agent.mcp.client import ToolResult
from ai_agent.persistence.checkpoints import migrate_checkpoints
from ai_agent.persistence.runs import migrate_runs

EXAMPLE = (
    Path(__file__).resolve().parents[3]
    / "docs/contracts/examples/ai-start.request.json"
)
PATH = "/internal/v1/investigations"


class DemoModel:
    async def chat(self, messages, *, tools=None):
        payload = json.loads(messages[-1].content)
        if tools is None:
            return ChatCompletion(
                json.dumps({"symptom_evidence_ids": [payload["evidence"][0]["id"]]})
            )
        if payload["observations"]:
            return ChatCompletion(
                json.dumps({"kind": "finish", "reason": "Evidence collected"})
            )
        scope = payload["scope"]
        return ChatCompletion(
            None,
            (
                ToolCall(
                    "demo-logs",
                    "search_logs",
                    {
                        "project_id": scope["project_id"],
                        "environment_id": scope["environment_id"],
                        "service_ids": scope["service_ids"],
                        **scope["window"],
                        "query": "HTTP 500",
                        "limit": 10,
                    },
                ),
            ),
        )


class DemoMCP:
    calls = 0

    async def discover(self):
        return [SimpleNamespace(name="search_logs")]

    async def call(self, name, arguments):
        self.calls += 1
        return ToolResult.model_validate(
            {
                "status": "ok",
                "summary": "Synthetic log",
                "source_refs": [
                    {
                        "source_type": "loki",
                        "source_id": "demo-log",
                        "observed_at": "2026-10-19T14:35:08Z",
                    },
                ],
                "items": [
                    {
                        "log_id": "demo-log",
                        "timestamp": "2026-10-19T14:35:08Z",
                        "service_name": "payment",
                        "level": "error",
                        "message": "Synthetic HTTP 500",
                    }
                ],
                "truncated": False,
            }
        )


def test_incidents_protocol_and_durable_worker():
    dsn = os.getenv("AI_AGENT_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("Set AI_AGENT_TEST_POSTGRES_DSN to a dedicated test database")
    schema = f"ai_test_{uuid4().hex}"
    settings = Settings(
        checkpoint_dsn=dsn,
        checkpoint_schema=schema,
        log_level="WARNING",
        _env_file=None,
    )

    async def scenario():
        async with await AsyncConnection.connect(dsn, autocommit=True) as admin:
            await admin.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
            )
            try:
                await migrate_checkpoints(settings)
                await migrate_runs(settings)
                await verify_run()
            finally:
                await admin.execute(
                    sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                )

    async def verify_run():
        authorized = []
        deliveries = []
        mcp = DemoMCP()

        async def verifier(authorization, action):
            assert authorization == "Bearer test-service-token"
            authorized.append(action)

        async def deliver(result):
            deliveries.append(result)
            return True

        @asynccontextmanager
        async def connect(_):
            yield mcp

        app = create_app(settings, authorize=verifier)

        def worker():
            return RunWorker(
                settings, model=DemoModel(), open_mcp=connect, deliver=deliver
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://ai-backend",
            headers={"Authorization": "Bearer test-service-token"},
        ) as client:
            body = json.loads(EXAMPLE.read_text())
            first_id = body["investigation_id"]
            headers = {"Idempotency-Key": first_id}
            response = await client.post(PATH, json=body, headers=headers)
            assert response.status_code == 202
            assert response.json()["investigation_id"] == first_id
            print(f"POST Start → {response.status_code} {response.json()['status']}")
            duplicate = await client.post(PATH, json=body, headers=headers)
            assert duplicate.json() == response.json()
            print(f"Повтор Start → {duplicate.status_code}, тот же запуск")
            conflict = await client.post(
                PATH, json={**body, "alert_summary": "Different"}, headers=headers
            )
            assert conflict.status_code == 409

            second_id = str(uuid4())
            second = {**body, "investigation_id": second_id}
            second_headers = {"Idempotency-Key": second_id}
            busy = await client.post(PATH, json=second, headers=second_headers)
            assert busy.status_code == 429
            assert busy.headers["Retry-After"] == "5"
            print(f"Второй запуск → {busy.status_code}, Retry-After: 5")

            status = await client.get(f"{PATH}/{first_id}")
            assert status.json()["id"] == first_id
            assert status.json()["status"] == "pending"

            assert sorted(
                await asyncio.gather(worker().run_once(), worker().run_once())
            ) == [False, True]
            assert mcp.calls == 1
            await worker().run_once()
            result = await client.get(f"{PATH}/{first_id}/result")
            stored = result.json()
            assert stored == deliveries[0]
            assert stored["status"] == "inconclusive"
            assert stored["evidence"][0]["source"]["source_type"] == "loki"
            assert len(stored["timeline"]) == 1
            print(
                "Воркеры → 1 вызов MCP, итог inconclusive, Evidence: 1, хронология: 1"
            )

            admitted = await client.post(PATH, json=second, headers=second_headers)
            assert admitted.status_code == 202
            assert (await client.post(f"{PATH}/{second_id}/cancel")).status_code == 202
            assert await worker().run_once()
            canceled = await client.get(f"{PATH}/{second_id}/result")
            assert canceled.json()["status"] == "canceled"
            assert mcp.calls == 1
            print("Отмена до выполнения → canceled, дополнительных MCP-вызовов нет")

            abandoned_id = str(uuid4())
            abandoned = {**body, "investigation_id": abandoned_id}
            assert (
                await client.post(
                    PATH, json=abandoned, headers={"Idempotency-Key": abandoned_id}
                )
            ).status_code == 202
            reached_checkpoint = asyncio.Event()

            class InterruptedModel(DemoModel):
                async def chat(self, messages, *, tools=None):
                    if tools and json.loads(messages[-1].content)["observations"]:
                        reached_checkpoint.set()
                        await asyncio.Event().wait()
                    return await super().chat(messages, tools=tools)

            interrupted = RunWorker(
                settings, model=InterruptedModel(), open_mcp=connect
            )
            running = asyncio.create_task(interrupted.run_once())
            try:
                await asyncio.wait_for(reached_checkpoint.wait(), 5)
                assert not await worker().run_once()
            finally:
                running.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await running
            assert await worker().run_once()
            recovered = await client.get(f"{PATH}/{abandoned_id}/result")
            assert recovered.json()["status"] == "failed"
            assert len(recovered.json()["evidence"]) == 1
            assert mcp.calls == 2
            print("Потеря воркера → failed, сохранённое Evidence доступно")
            assert set(authorized) == {"start", "cancel", "readback"}

    asyncio.run(scenario())
