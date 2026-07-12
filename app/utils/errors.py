from __future__ import annotations


class PolicyLensError(Exception):
    """Base exception for PolicyLens application."""
    pass


class LLMServiceError(PolicyLensError):
    """Raised when the LLM client fails to generate text or encounters an API error."""
    pass


class RetrievalError(PolicyLensError):
    """Raised when vector search fails or the collection is unavailable."""
    pass


class ConfigurationError(PolicyLensError):
    """Raised when configuration is missing or invalid."""
    pass
