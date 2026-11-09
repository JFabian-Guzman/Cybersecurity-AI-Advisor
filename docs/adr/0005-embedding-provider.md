# 0005. Embedding provider and embedding job

- Status: approved
- Date: 2026-11-08
- Deciders: Andrés Víquez, Fabián Guzmán

## Context

Sprint 4 adds semantic retrieval over the chunks produced by the worker (ADR-0003). Each chunk
needs a vector embedding stored on `chunks.embedding` (pgvector), and Sprint 5's chatbot will
retrieve chunks by similarity to a user question.

ADR-0001 requires a provider-agnostic interface with a local Ollama option, and Sprint 4 adds a
fallback story: when the primary provider fails or rate-limits, embedding retries against a local
Ollama model.

Constraints that shape this decision:

- Cost: this is a two-person portfolio project; recurring cost should be zero or close to it.
- Volume: a scan stores at most 2,000 chunks (`MAX_CHUNKS_PER_SCAN`) of up to 1,500 characters
  (roughly 375 tokens each, using our `ceil(len / 4)` heuristic), so about 750k tokens per scan
  in the worst case.
- Deployment: the primary provider must be reachable from Render, so it has to be hosted.
- Compatibility: vectors from different models live in different vector spaces and cannot be
  compared, even when they share a dimension. A pgvector column also has a fixed dimension.
- Data: Sprint 1 to 4 scope is public HTTPS repositories only; private repositories (OAuth) are a
  later sprint.
- Job runtime: RQ kills jobs that run longer than 180 seconds by default.

## Decision

### Provider and model

- Primary provider: Google Gemini API, model `gemini-embedding-001`, on the free tier.
- Output dimension: 768 (`outputDimensionality: 768`), stored as `vector(768)`.
- Task types: `RETRIEVAL_DOCUMENT` when embedding chunks, `RETRIEVAL_QUERY` when embedding a
  user question.
- Similarity: cosine distance (pgvector `<=>`, `vector_cosine_ops` index). Gemini only
  pre-normalizes 3072-dimension vectors; cosine distance does not require normalized input, so
  no manual normalization step is needed.
- Fallback provider: local Ollama with `nomic-embed-text` (768 dimensions).

### Provider interface

We will add a small `EmbeddingProvider` protocol in the backend that exposes the model name and
a batch embedding call with a document/query mode. Gemini and Ollama are implementations of it.
Configuration (API key, model, dimension, Ollama URL) comes from environment variables only; the
API key is never logged or committed. Andrés owns this layer; the embedding pipeline consumes it.

### Mixed vector spaces

Each chunk stores the model that produced its embedding in a new `chunks.embedding_model` column.
Retrieval embeds the question with a given model and only compares it against chunks embedded by
that same model. A chunk with a NULL embedding is treated as not embedded and is excluded from
retrieval.

### Separate embedding job

Embedding does not run inside `run_scan`. When a scan succeeds, `run_scan` enqueues a separate
`embed_scan(scan_id)` job on a dedicated `embeddings` RQ queue, served by its own worker process.

- The scan is marked `succeeded` before embedding starts, so findings, report, and export are
  available at the same speed as today.
- The embedding job paces its requests to stay inside the provider's per-minute limits and sets
  an explicit `job_timeout` derived from the per-scan embedding cap, instead of the 180-second
  default.
- The embedding job tolerates chunks that disappear while it runs (re-scan retention or
  repository disconnect): updates that match no rows are ignored, not treated as errors.
- Embedding failures, cap hits, and per-user rate-limit skips are logged with an actionable
  reason. They never change the scan status.

### Data policy

Chunk text is sanitized before it is sent to any provider (ADR-0003 obligation). On the Gemini
free tier, prompts may be used to improve Google products and may be read by human reviewers.
This is acceptable while only public repositories are scanned. Billing must be enabled (paid
tier, where data is not used for product improvement) before private repository support ships.

## Consequences

### Positive

- Zero recurring cost while the project stays inside the free tier.
- Scans finish as fast as before; slow embedding never blocks findings or reports.
- A dedicated queue keeps a large embedding job from delaying other users' scans.
- Recording `embedding_model` per chunk makes the Ollama fallback safe and keeps provider issues
  traceable.
- Matching dimensions (768) let one column hold both providers' vectors.
- `gemini-embedding-001` has an earliest announced shutdown of 2028-05-14, beyond the project
  timeline.

### Negative

- Free tier limits are low: 100 requests per minute, 30,000 tokens per minute, and 1,000
  requests per day. A worst-case scan (about 750k tokens) needs roughly 25 minutes to embed, and
  a busy day can exhaust the daily quota.
- Chunks are not searchable until the embedding job finishes; Sprint 5 must handle a scan whose
  embeddings are still in progress.
- One more queue and worker process to run locally and, eventually, to deploy.
- Retrieval quality on fallback-embedded chunks can differ from Gemini-embedded chunks, and the
  two sets cannot be ranked against each other directly.
- Free tier data terms are not suitable for private code; switching to the paid tier is a
  required step before private repositories.

## Alternatives considered

- OpenAI `text-embedding-3-small`: cheapest pay-as-you-go option and supports 768 dimensions.
  Not chosen because it requires a payment method from day one.
- Voyage AI: has a code-specialized model, but its output dimensions (256, 512, 1024, 2048) do
  not match the 768-dimension Ollama fallback.
- Ollama only: free and private, but not available on Render, which would leave the deployed app
  without embeddings.
- Embedding inside `run_scan`: simplest, but free tier pacing would push scans far past the RQ
  timeout and keep them in `running` for minutes.
- Lower the per-scan cap until embedding fits in a scan job: keeps one job, but would embed only
  a small part of each repository and weaken retrieval.
- Raise the scan job timeout: keeps one job, but scans would stay `running` for up to 25 minutes
  and block the worker.
