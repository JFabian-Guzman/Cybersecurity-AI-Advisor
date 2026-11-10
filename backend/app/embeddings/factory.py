from __future__ import annotations

from app.core import config
from app.embeddings.budget import EmbeddingBudget
from app.embeddings.gemini import GeminiEmbeddingProvider
from app.embeddings.provider import EmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """Build the primary embedding provider from environment configuration (ADR-0005)."""
    return GeminiEmbeddingProvider(
        api_key=config.GEMINI_API_KEY,
        model=config.GEMINI_EMBEDDING_MODEL,
        dimensions=config.EMBEDDING_DIMENSIONS,
        batch_size=config.EMBEDDING_BATCH_SIZE,
        timeout_seconds=config.EMBEDDING_REQUEST_TIMEOUT_SECONDS,
    )


def new_scan_budget() -> EmbeddingBudget:
    """Create a fresh per-scan embedding budget from environment configuration."""
    return EmbeddingBudget(
        max_requests=config.EMBEDDING_MAX_REQUESTS_PER_SCAN,
        max_tokens=config.EMBEDDING_MAX_TOKENS_PER_SCAN,
    )
