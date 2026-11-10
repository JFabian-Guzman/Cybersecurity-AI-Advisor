from __future__ import annotations

import httpx

from app.embeddings.provider import (
    EmbeddingConfigError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingTask,
)

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

_TASK_TYPES: dict[EmbeddingTask, str] = {
    EmbeddingTask.DOCUMENT: "RETRIEVAL_DOCUMENT",
    EmbeddingTask.QUERY: "RETRIEVAL_QUERY",
}
_REDACTED = "[REDACTED]"


def _error_detail(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])
    except ValueError, KeyError, TypeError:
        return response.text[:200]


class GeminiEmbeddingProvider:
    """Embeds text with the Gemini API ``batchEmbedContents`` endpoint (ADR-0005)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
        batch_size: int,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise EmbeddingConfigError("GEMINI_API_KEY is not set; set it in the environment to enable embeddings")
        if batch_size < 1:
            raise EmbeddingConfigError(f"EMBEDDING_BATCH_SIZE must be at least 1, got {batch_size}")

        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        # The key travels in a header, not the URL, so it never appears in request URLs or httpx errors.
        self._client = httpx.Client(
            base_url=GEMINI_API_BASE_URL,
            headers={"x-goog-api-key": api_key},
            timeout=timeout_seconds,
            transport=transport,
        )

    @property
    def model_name(self) -> str:
        return f"gemini/{self._model}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def max_batch_size(self) -> int:
        return self._batch_size

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        if not texts:
            return []
        if len(texts) > self._batch_size:
            raise ValueError(f"Gemini provider accepts at most {self._batch_size} texts per call, got {len(texts)}")

        response = self._post(self._build_payload(texts, task))
        return self._parse_vectors(response, expected_count=len(texts))

    def close(self) -> None:
        self._client.close()

    def _build_payload(self, texts: list[str], task: EmbeddingTask) -> dict[str, object]:
        return {
            "requests": [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": _TASK_TYPES[task],
                    "outputDimensionality": self._dimensions,
                }
                for text in texts
            ]
        }

    def _post(self, payload: dict[str, object]) -> httpx.Response:
        try:
            response = self._client.post(f"/models/{self._model}:batchEmbedContents", json=payload)
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(self._redact(f"Gemini request failed: {exc}")) from exc

        if response.status_code == 429:
            raise EmbeddingRateLimitError(
                "Gemini rate limit reached (HTTP 429); pace batches to stay under the per-minute limits "
                "or retry after the window resets"
            )
        if response.status_code >= 400:
            detail = _error_detail(response)
            raise EmbeddingProviderError(self._redact(f"Gemini returned HTTP {response.status_code}: {detail}"))
        return response

    def _parse_vectors(self, response: httpx.Response, expected_count: int) -> list[list[float]]:
        try:
            vectors = [[float(value) for value in item["values"]] for item in response.json()["embeddings"]]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingProviderError("Gemini returned an unexpected response shape") from exc

        if len(vectors) != expected_count:
            raise EmbeddingProviderError(f"Gemini returned {len(vectors)} embeddings for {expected_count} texts")
        for vector in vectors:
            if len(vector) != self._dimensions:
                raise EmbeddingProviderError(
                    f"Gemini returned a vector of dimension {len(vector)}, expected {self._dimensions}"
                )
        return vectors

    def _redact(self, message: str) -> str:
        return message.replace(self._api_key, _REDACTED)
