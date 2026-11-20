class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMTransportError(LLMError):
    pass


class LLMHTTPError(LLMError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Local inference server returned HTTP {status_code}")


class LLMResponseError(LLMError):
    pass
