import json
import logging

from ai_agent.core.logging import JsonFormatter, request_id


def test_json_log_contains_request_id():
    token = request_id.set("request-123")
    try:
        line = JsonFormatter().format(
            logging.LogRecord(
                "ai_agent.test", logging.INFO, __file__, 1, "done", (), None
            )
        )
    finally:
        request_id.reset(token)

    assert json.loads(line)["request_id"] == "request-123"
