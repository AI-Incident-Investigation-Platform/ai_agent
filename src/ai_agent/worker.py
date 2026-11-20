import argparse
import asyncio

from ai_agent.application.services.run_worker import RunWorker
from ai_agent.core.config import Settings
from ai_agent.core.logging import configure_logging
from ai_agent.core.service_auth import ResultDelivery
from ai_agent.persistence.checkpoints import migrate_checkpoints
from ai_agent.persistence.runs import migrate_runs


async def main(command: str) -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    if command == "migrate":
        await migrate_checkpoints(settings)
        await migrate_runs(settings)
        return

    if settings.incidents_url is not None:
        if settings.auth_url is None or settings.auth_client_secret is None:
            raise SystemExit("Configure AUTH_URL and AUTH_CLIENT_SECRET for callbacks")
        delivery = ResultDelivery(
            str(settings.auth_url),
            str(settings.incidents_url),
            settings.auth_client_secret.get_secret_value(),
        )
    else:
        delivery = None
    await RunWorker(settings, deliver=delivery).run_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("migrate", "run"))
    asyncio.run(main(parser.parse_args().command))
