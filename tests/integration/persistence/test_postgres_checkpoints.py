import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from psycopg import AsyncConnection, sql
from psycopg.conninfo import make_conninfo

from ai_agent.agent.decisions import ActionDecision, FinishDecision
from ai_agent.agent.graph import build_graph
from ai_agent.application.contracts import StartAIRequest
from ai_agent.application.mappers import to_graph_state
from ai_agent.core.config import Settings
from ai_agent.mcp.safe_tools import IncidentContextArgs
from ai_agent.persistence.checkpoints import (
    CheckpointStorageError,
    connect_checkpointer,
    investigation_checkpoint_config,
    migrate_checkpoints,
)

EXAMPLE = (
    Path(__file__).resolve().parents[3]
    / "docs/contracts/examples/ai-start.request.json"
)


class Decisions:
    async def decide(self, current):
        context = current["context"]
        if current["step"] == 0:
            return ActionDecision(
                kind="action",
                tool_call_id="test-call",
                name="get_incident_context",
                arguments={
                    "incident_id": str(context.incident_id),
                    "investigation_id": str(context.investigation_id),
                },
            )
        return FinishDecision(kind="finish", reason="Done")


class Executor:
    def __init__(self, *, resuming=False):
        self.calls = 0
        self.resuming = resuming

    async def execute(self, name, arguments):
        self.calls += 1
        if self.resuming:
            raise AssertionError("Resume repeated the saved tool call")
        return {
            "status": "ok",
            "source_refs": [{"source_type": "manual", "source_id": "incident-record"}],
            "items": [{"incident_id": arguments["incident_id"]}],
            "truncated": False,
        }


def graph(saver, executor):
    return build_graph(
        Decisions(),
        executor,
        {"get_incident_context": IncidentContextArgs},
        checkpointer=saver,
    )


async def resume(investigation_id):
    async with connect_checkpointer(Settings(_env_file=None)) as saver:
        executor = Executor(resuming=True)
        flow = graph(saver, executor)
        config = investigation_checkpoint_config(investigation_id)
        saved = await flow.aget_state(config)
        assert saved.next == ("decide",)
        assert saved.values["tool_calls_count"] == 1
        assert saved.values["context"].investigation_id == investigation_id
        final = await flow.ainvoke(None, config, durability="sync")
        assert final["terminal_status"] == "ready_for_finalization"
        assert final["tool_calls_count"] == 1
        assert final["deadline_at"] == saved.values["deadline_at"]
        assert final["evidence"] == saved.values["evidence"]
        assert executor.calls == 0


def test_postgres_resume_in_new_process_and_thread_isolation():
    dsn = os.getenv("AI_AGENT_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("Set AI_AGENT_TEST_POSTGRES_DSN to a dedicated test database")
    schema = f"ai_test_{uuid4().hex}"
    settings = Settings(checkpoint_dsn=dsn, checkpoint_schema=schema, _env_file=None)
    request = StartAIRequest.model_validate_json(EXAMPLE.read_bytes())
    config = investigation_checkpoint_config(request.investigation_id)

    async def test():
        async with await AsyncConnection.connect(dsn, autocommit=True) as admin:
            await admin.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
            )
            try:
                await migrate_checkpoints(settings)
                await migrate_checkpoints(settings)
                denied = Settings(
                    checkpoint_dsn=make_conninfo(dsn, user=f"denied_{uuid4().hex}"),
                    checkpoint_schema=schema,
                    _env_file=None,
                )
                with pytest.raises(
                    CheckpointStorageError,
                    match="^Checkpoint database operation failed$",
                ):
                    async with connect_checkpointer(denied):
                        pytest.fail("Unknown database role connected")
                async with connect_checkpointer(settings) as saver:
                    executor = Executor()
                    flow = graph(saver, executor)
                    await flow.ainvoke(
                        to_graph_state(request),
                        config,
                        interrupt_after=["normalize"],
                        durability="sync",
                    )
                    assert executor.calls == 1
                    other = investigation_checkpoint_config(uuid4())
                    assert not (await flow.aget_state(other)).values
                    with pytest.raises(
                        ValueError, match="Checkpoint thread must match"
                    ):
                        await flow.ainvoke(to_graph_state(request), other)
                    assert executor.calls == 1
                child = await asyncio.create_subprocess_exec(
                    sys.executable,
                    __file__,
                    str(request.investigation_id),
                    env={
                        **os.environ,
                        "AI_AGENT_CHECKPOINT_DSN": dsn,
                        "AI_AGENT_CHECKPOINT_SCHEMA": schema,
                    },
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                try:
                    _, errors = await asyncio.wait_for(child.communicate(), timeout=20)
                finally:
                    if child.returncode is None:
                        child.kill()
                        await child.wait()
                assert child.returncode == 0, errors.decode()
                async with connect_checkpointer(settings) as saver:
                    values = (await graph(saver, Executor()).aget_state(config)).values
                    assert values["step"] == 2
                    assert len(values["evidence"]) == 1
            finally:
                await admin.execute(
                    sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                )

    asyncio.run(test())


if __name__ == "__main__":
    asyncio.run(resume(UUID(sys.argv[1])))
