import os

from dotenv import load_dotenv

load_dotenv()


def _normalized_database_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://cybersec:cybersec@localhost:5433/cybersec",
    )
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


DATABASE_URL = _normalized_database_url()

# Embeddings (ADR-0005). The API key comes from the environment only and must never be logged.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
# Must match the vector size of chunks.embedding.
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
# 50 chunks of ~375 tokens stay under the free tier's 30k tokens per minute in a single request.
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
EMBEDDING_REQUEST_TIMEOUT_SECONDS = float(os.getenv("EMBEDDING_REQUEST_TIMEOUT_SECONDS", "30"))
EMBEDDING_MAX_REQUESTS_PER_SCAN = int(os.getenv("EMBEDDING_MAX_REQUESTS_PER_SCAN", "50"))
EMBEDDING_MAX_TOKENS_PER_SCAN = int(os.getenv("EMBEDDING_MAX_TOKENS_PER_SCAN", "300000"))
