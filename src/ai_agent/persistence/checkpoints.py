from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg import AsyncConnection, Error, sql
from psycopg.rows import dict_row

from ai_agent.core.config import Settings
from ai_agent.domain.models import ExecutionBudget, InvestigationContext, TimeWindow


class CheckpointStorageError(RuntimeError):
    pass


def investigation_checkpoint_config(investigation_id: UUID) -> RunnableConfig:
    return {"configurable": {"thread_id": str(investigation_id), "checkpoint_ns": ""}}


@asynccontextmanager
async def connect_storage(settings: Settings) -> AsyncIterator[AsyncConnection]:
    if settings.checkpoint_dsn is None or settings.checkpoint_schema is None:
        raise CheckpointStorageError(
            "Checkpoint database and schema must be configured"
        )

    try:
        async with await AsyncConnection.connect(
            settings.checkpoint_dsn.get_secret_value(),
            connect_timeout=5,
            autocommit=True,
            prepare_threshold=0,
            row_factory=dict_row,
        ) as conn:
            await conn.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(settings.checkpoint_schema)
                )
            )
            cursor = await conn.execute(
                "SELECT pg_catalog.current_schema() = %s::name AS available",
                (settings.checkpoint_schema,),
            )
            row = await cursor.fetchone()
            if row is None or not row["available"]:
                raise CheckpointStorageError("Checkpoint schema is unavailable")

            yield conn
    except Error:
        raise CheckpointStorageError("Checkpoint database operation failed") from None


@asynccontextmanager
async def connect_checkpointer(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    async with connect_storage(settings) as conn:
        serde = JsonPlusSerializer(
            allowed_msgpack_modules=[
                (model.__module__, model.__name__)
                for model in (InvestigationContext, ExecutionBudget, TimeWindow)
            ]
        )
        yield AsyncPostgresSaver(conn, serde=serde)


async def migrate_checkpoints(settings: Settings) -> None:
    async with connect_checkpointer(settings) as saver:
        await saver.setup()
