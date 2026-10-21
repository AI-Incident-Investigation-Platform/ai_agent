import logging
import re
from uuid import uuid4

from fastapi import FastAPI, Request

from ai_agent.api.routes.health import router as health_router
from ai_agent.core.config import Settings
from ai_agent.core.logging import configure_logging, request_id

logger = logging.getLogger("ai_agent.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="AI Incident Investigator AI Backend")
    app.state.settings = settings
    app.include_router(health_router)

    @app.middleware("http")
    async def correlate_request(request: Request, call_next):
        supplied_id = request.headers.get("X-Request-ID", "")
        correlation_id = (
            supplied_id if _REQUEST_ID_PATTERN.fullmatch(supplied_id) else str(uuid4())
        )
        token = request_id.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = correlation_id
            logger.info("request completed", extra={"path": request.url.path})
            return response
        finally:
            request_id.reset(token)

    return app


app = create_app()
