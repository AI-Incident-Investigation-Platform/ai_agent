import asyncio

import pytest

from ai_agent.core.config import Settings
from ai_agent.persistence.checkpoints import (
    CheckpointStorageError,
    connect_checkpointer,
)


def test_connection_error_does_not_expose_dsn():
    settings = Settings(
        checkpoint_dsn="postgresql://user:private-marker@invalid.invalid:bad/db",
        checkpoint_schema="ai_checkpoints",
    )

    async def connect():
        async with connect_checkpointer(settings):
            pytest.fail("Malformed DSN was accepted")

    with pytest.raises(CheckpointStorageError) as error:
        asyncio.run(connect())
    assert str(error.value) == "Checkpoint database operation failed"
    assert error.value.__suppress_context__
