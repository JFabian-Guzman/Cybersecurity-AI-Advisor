from __future__ import annotations

import json
from collections.abc import Callable, Mapping

import httpx
import pytest

from app.core import config
from app.embeddings.budget import EmbeddingBudget, estimate_tokens
from app.embeddings.factory import get_embedding_provider, new_scan_budget
from app.embeddings.gemini import GeminiEmbeddingProvider
from app.embeddings.provider import (
    EmbeddingBudgetExceededError,
    EmbeddingConfigError,
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingTask,
)

API_KEY = "fake-gemini-key"
DIMENSIONS = 4

Handler = Callable[[httpx.Request], httpx.Response]


def _provider(handler: Handler, batch_size: int = 3) -> GeminiEmbeddingProvider:
    return GeminiEmbeddingProvider(
        api_key=API_KEY,
        model="gemini-embedding-001",
        dimensions=DIMENSIONS,
        batch_size=batch_size,
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )


def _embeddings_handler(captured: list[httpx.Request], dimensions: int = DIMENSIONS) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        body = json.loads(request.content)
        vectors = [{"values": [0.1] * dimensions} for _ in body["requests"]]
        return httpx.Response(200, json={"embeddings": vectors})

    return handler


def _status_handler(status_code: int, payload: Mapping[str, object]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return handler


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


def test_provider_satisfies_protocol() -> None:
    provider: EmbeddingProvider = _provider(_embeddings_handler([]))
    assert provider.model_name == "gemini/gemini-embedding-001"
    assert provider.dimensions == DIMENSIONS
    assert provider.max_batch_size == 3


def test_embed_documents_sends_one_batch_request() -> None:
    captured: list[httpx.Request] = []
    provider = _provider(_embeddings_handler(captured))

    vectors = provider.embed(["FROM python:latest", "USER root"], EmbeddingTask.DOCUMENT)

    assert vectors == [[0.1] * DIMENSIONS, [0.1] * DIMENSIONS]
    assert len(captured) == 1
    request = captured[0]
    assert request.url.path == "/v1beta/models/gemini-embedding-001:batchEmbedContents"
    assert request.headers["x-goog-api-key"] == API_KEY
    body = json.loads(request.content)
    texts = [item["content"]["parts"][0]["text"] for item in body["requests"]]
    assert texts == ["FROM python:latest", "USER root"]
    assert {item["taskType"] for item in body["requests"]} == {"RETRIEVAL_DOCUMENT"}
    assert {item["outputDimensionality"] for item in body["requests"]} == {DIMENSIONS}
    assert {item["model"] for item in body["requests"]} == {"models/gemini-embedding-001"}


def test_embed_query_uses_retrieval_query_task_type() -> None:
    captured: list[httpx.Request] = []
    provider = _provider(_embeddings_handler(captured))

    provider.embed(["Which containers run as root?"], EmbeddingTask.QUERY)

    body = json.loads(captured[0].content)
    assert body["requests"][0]["taskType"] == "RETRIEVAL_QUERY"


def test_embed_empty_list_makes_no_request() -> None:
    captured: list[httpx.Request] = []
    provider = _provider(_embeddings_handler(captured))

    assert provider.embed([], EmbeddingTask.DOCUMENT) == []
    assert captured == []


def test_embed_rejects_batches_larger_than_max_batch_size() -> None:
    provider = _provider(_embeddings_handler([]))
    with pytest.raises(ValueError, match="at most 3"):
        provider.embed(["a", "b", "c", "d"], EmbeddingTask.DOCUMENT)


def test_rate_limit_raises_rate_limit_error() -> None:
    provider = _provider(_status_handler(429, {"error": {"message": "Resource exhausted"}}))
    with pytest.raises(EmbeddingRateLimitError):
        provider.embed(["a"], EmbeddingTask.DOCUMENT)


def test_http_error_message_never_contains_api_key() -> None:
    echoed = {"error": {"message": f"API key {API_KEY} not valid"}}
    provider = _provider(_status_handler(400, echoed))

    with pytest.raises(EmbeddingProviderError) as exc_info:
        provider.embed(["a"], EmbeddingTask.DOCUMENT)

    assert API_KEY not in str(exc_info.value)
    assert "HTTP 400" in str(exc_info.value)


def test_network_error_raises_provider_error_without_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"connection refused for {API_KEY}", request=request)

    provider = _provider(handler)

    with pytest.raises(EmbeddingProviderError) as exc_info:
        provider.embed(["a"], EmbeddingTask.DOCUMENT)

    assert API_KEY not in str(exc_info.value)


def test_unexpected_dimension_raises() -> None:
    provider = _provider(_embeddings_handler([], dimensions=DIMENSIONS + 1))
    with pytest.raises(EmbeddingProviderError, match="dimension"):
        provider.embed(["a"], EmbeddingTask.DOCUMENT)


def test_embedding_count_mismatch_raises() -> None:
    provider = _provider(_status_handler(200, {"embeddings": [{"values": [0.1] * DIMENSIONS}]}))
    with pytest.raises(EmbeddingProviderError, match="1 embeddings for 2 texts"):
        provider.embed(["a", "b"], EmbeddingTask.DOCUMENT)


def test_unexpected_response_shape_raises() -> None:
    provider = _provider(_status_handler(200, {"unexpected": []}))
    with pytest.raises(EmbeddingProviderError, match="unexpected response shape"):
        provider.embed(["a"], EmbeddingTask.DOCUMENT)


def test_missing_api_key_raises_config_error() -> None:
    with pytest.raises(EmbeddingConfigError, match="GEMINI_API_KEY"):
        GeminiEmbeddingProvider(
            api_key="",
            model="gemini-embedding-001",
            dimensions=DIMENSIONS,
            batch_size=3,
            timeout_seconds=5,
        )


# ---------------------------------------------------------------------------
# Per-scan budget
# ---------------------------------------------------------------------------


def test_estimate_tokens_uses_chunk_heuristic() -> None:
    assert estimate_tokens(["abcd", "abcde"]) == 1 + 2


def test_budget_reserve_charges_requests_and_tokens() -> None:
    budget = EmbeddingBudget(max_requests=2, max_tokens=100)

    budget.reserve(["a" * 40])

    assert budget.requests_used == 1
    assert budget.tokens_used == 10


def test_budget_stops_at_token_cap_without_charging() -> None:
    budget = EmbeddingBudget(max_requests=10, max_tokens=15)
    budget.reserve(["a" * 40])

    with pytest.raises(EmbeddingBudgetExceededError, match="EMBEDDING_MAX_TOKENS_PER_SCAN"):
        budget.reserve(["a" * 40])

    assert budget.requests_used == 1
    assert budget.tokens_used == 10


def test_budget_stops_at_request_cap_without_charging() -> None:
    budget = EmbeddingBudget(max_requests=1, max_tokens=1000)
    budget.reserve(["a"])

    with pytest.raises(EmbeddingBudgetExceededError, match="EMBEDDING_MAX_REQUESTS_PER_SCAN"):
        budget.reserve(["a"])

    assert budget.requests_used == 1


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_without_api_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(EmbeddingConfigError):
        get_embedding_provider()


def test_factory_builds_gemini_provider_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEY", API_KEY)
    monkeypatch.setattr(config, "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    monkeypatch.setattr(config, "EMBEDDING_DIMENSIONS", 768)
    monkeypatch.setattr(config, "EMBEDDING_BATCH_SIZE", 50)

    provider = get_embedding_provider()

    assert provider.model_name == "gemini/gemini-embedding-001"
    assert provider.dimensions == 768
    assert provider.max_batch_size == 50
    provider.close()


def test_new_scan_budget_uses_config_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "EMBEDDING_MAX_REQUESTS_PER_SCAN", 7)
    monkeypatch.setattr(config, "EMBEDDING_MAX_TOKENS_PER_SCAN", 1234)

    budget = new_scan_budget()

    assert budget.max_requests == 7
    assert budget.max_tokens == 1234
