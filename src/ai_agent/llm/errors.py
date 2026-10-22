class LLMError(Exception):
    """A local inference request failed."""


class LLMTimeoutError(LLMError):
    """The local inference request exceeded its deadline."""


class LLMTransportError(LLMError):
    """The local inference server could not be reached."""


class LLMHTTPError(LLMError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Local inference server returned HTTP {status_code}")


class LLMResponseError(LLMError):
    """The local inference response is malformed, empty, or truncated."""
