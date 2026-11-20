import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from ai_agent.agent.finalization import finalize_investigation
from ai_agent.agent.graph import build_graph
from ai_agent.agent.model_decisions import ModelDecisions
from ai_agent.application.contracts import StartAIRequest
from ai_agent.application.mappers import to_graph_state
from ai_agent.core.config import Settings
from ai_agent.llm.providers.llama_cpp import LlamaCppProvider
from ai_agent.llm.types import ChatProvider
from ai_agent.mcp.client import connect_mcp
from ai_agent.mcp.safe_tools import SCHEMAS, SafeToolExecutor
from ai_agent.persistence.checkpoints import (
    CheckpointStorageError,
    connect_checkpointer,
    investigation_checkpoint_config,
)
from ai_agent.persistence.runs import RunRegistry

logger = logging.getLogger(__name__)
Delivery = Callable[[dict], Awaitable[bool]]


class RunWorker:
    def __init__(
        self,
        settings: Settings,
        *,
        deliver: Delivery | None = None,
        model: ChatProvider | None = None,
        open_mcp=connect_mcp,
    ):
        self.settings = settings
        self.registry = RunRegistry(settings)
        self.deliver = deliver
        self.model = model or LlamaCppProvider(settings)
        self.open_mcp = open_mcp

    async def run_once(self) -> bool:
        async with self.registry.worker_session() as conn:
            if conn is None:
                return False
            if self.deliver is not None and (
                due := await self.registry.due_result(conn)
            ):
                await self.registry.record_delivery(
                    conn, due, await self.deliver(due["result"])
                )
            row, abandoned = await self.registry.claim(conn)
            if row is None:
                return False
            await self._run(conn, row, abandoned)
            return True

    async def _run(self, conn, row: dict, abandoned: bool) -> None:
        request = StartAIRequest.model_validate(row["request"])
        run_id = request.investigation_id
        config = investigation_checkpoint_config(run_id)
        state = to_graph_state(request)
        state["deadline_at"] = row["deadline_at"].timestamp()
        cancel_requested = row["cancel_requested"]
        finished = asyncio.Event()
        stop = None

        async def monitor() -> None:
            nonlocal cancel_requested
            while not finished.is_set():
                cursor = await conn.execute(
                    "SELECT cancel_requested FROM ai_runs WHERE id = %s", (run_id,)
                )
                current = await cursor.fetchone()
                cancel_requested = current["cancel_requested"]
                try:
                    await asyncio.wait_for(finished.wait(), timeout=0.25)
                except TimeoutError:
                    pass

        async def investigate(saver):
            if abandoned:
                return
            async with asyncio.timeout(
                max(0, state["deadline_at"] - datetime.now(UTC).timestamp())
            ):
                async with self.open_mcp(self.settings) as mcp:
                    tools = {item.name for item in await mcp.discover()}
                    schemas = {
                        name: schema
                        for name, schema in SCHEMAS.items()
                        if name in tools
                    }
                    graph = build_graph(
                        ModelDecisions(self.model, schemas),
                        SafeToolExecutor(state["context"], mcp),
                        schemas,
                        checkpointer=saver,
                        is_cancel_requested=lambda _: cancel_requested,
                    )
                    return await graph.ainvoke(state, config, durability="sync")

        async with connect_checkpointer(self.settings) as saver:
            if abandoned:
                saved = await saver.aget_tuple(config)
                if saved is not None:
                    state.update(saved.checkpoint["channel_values"])
                if not state.get("terminal_status"):
                    stop = "failed"
            if cancel_requested:
                stop = "canceled"
            elif datetime.now(UTC).timestamp() >= state["deadline_at"]:
                stop = "timed_out"
            if not abandoned and stop is None:
                async with asyncio.TaskGroup() as group:
                    group.create_task(monitor())
                    try:
                        state = await investigate(saver)
                    except TimeoutError:
                        stop = "timed_out"
                    except CheckpointStorageError:
                        raise
                    except Exception:
                        stop = "failed"
                    finally:
                        finished.set()
                if stop:
                    saved = await saver.aget_tuple(config)
                    if saved is not None:
                        state.update(saved.checkpoint["channel_values"])
            if stop:
                state["terminal_status"] = stop
            result = await finalize_investigation(
                state, self.model, is_cancel_requested=lambda _: cancel_requested
            )
            if not await self.registry.finish(conn, result):
                state["terminal_status"] = "canceled"
                state.pop("result_callback", None)
                result = await finalize_investigation(state, self.model)
                if not await self.registry.finish(conn, result):
                    raise CheckpointStorageError("Could not persist terminal result")

    async def run_forever(self) -> None:
        while True:
            try:
                worked = await self.run_once()
            except Exception:
                logger.warning("Investigation worker iteration failed")
                worked = False
            if not worked:
                await asyncio.sleep(1)
