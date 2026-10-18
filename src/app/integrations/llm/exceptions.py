class LLMError(Exception):
    """Base class for all LLM integration failures."""


class LLMUnavailableError(LLMError):
    """Provider unreachable, timed out, or returned a 5xx."""


class LLMRateLimitError(LLMError):
    """Provider rate limit hit (even after SDK retries)."""


class LLMBadResponseError(LLMError):
    """Provider replied but with an empty or malformed completion."""