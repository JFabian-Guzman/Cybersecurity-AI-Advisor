from __future__ import annotations

from enum import StrEnum
from typing import Protocol


class EmbeddingTask(StrEnum):
    """Whether the text is content to index or a question to search with."""

    DOCUMENT = "document"
    QUERY = "query"


class EmbeddingError(RuntimeError):
    """Base class for every embedding failure; callers log it and never fail the scan."""


class EmbeddingConfigError(EmbeddingError):
    """The provider is missing configuration (for example, no API key)."""


class EmbeddingProviderError(EmbeddingError):
    """The provider call failed or returned something unusable."""


class EmbeddingRateLimitError(EmbeddingProviderError):
    """The provider rejected the call because a rate limit was hit (HTTP 429)."""


class EmbeddingBudgetExceededError(EmbeddingError):
    """The per-scan embedding cap would be exceeded by the next batch."""


class EmbeddingProvider(Protocol):
    """Contract shared by every embedding backend (Gemini now, Ollama as fallback)."""

    @property
    def model_name(self) -> str:
        """Identifier stored in chunks.embedding_model, e.g. ``gemini/gemini-embedding-001``."""
        ...

    @property
    def dimensions(self) -> int: ...

    @property
    def max_batch_size(self) -> int: ...

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        """Embed up to ``max_batch_size`` texts in one call, returning vectors in input order."""
        ...

    def close(self) -> None: ...
