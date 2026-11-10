from __future__ import annotations

from dataclasses import dataclass

from app.embeddings.provider import EmbeddingBudgetExceededError
from app.models.chunk import Chunk


def estimate_tokens(texts: list[str]) -> int:
    """Estimate tokens with the same heuristic used for chunks.token_count."""
    return sum(Chunk.compute_token_count(text) for text in texts)


@dataclass
class EmbeddingBudget:
    """Per-scan cap on embedding requests and estimated tokens (ADR-0005).

    The embedding job calls ``reserve`` before each batch; when the cap would be exceeded it
    raises, so the job stops cleanly with an actionable reason instead of truncating silently.
    """

    max_requests: int
    max_tokens: int
    requests_used: int = 0
    tokens_used: int = 0

    def reserve(self, texts: list[str]) -> None:
        tokens = estimate_tokens(texts)
        if self.requests_used + 1 > self.max_requests:
            raise EmbeddingBudgetExceededError(
                f"Per-scan embedding request cap reached ({self.max_requests} requests); "
                "raise EMBEDDING_MAX_REQUESTS_PER_SCAN to embed more of this scan"
            )
        if self.tokens_used + tokens > self.max_tokens:
            raise EmbeddingBudgetExceededError(
                f"Per-scan embedding token cap reached ({self.tokens_used} used + {tokens} requested "
                f"> {self.max_tokens}); raise EMBEDDING_MAX_TOKENS_PER_SCAN to embed more of this scan"
            )
        self.requests_used += 1
        self.tokens_used += tokens
