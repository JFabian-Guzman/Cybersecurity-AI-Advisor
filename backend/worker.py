from __future__ import annotations

import os

import structlog
from redis import Redis
from rq import Queue, Worker

log = structlog.get_logger()


def get_redis() -> Redis:
    return Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def get_queue(redis: Redis | None = None) -> Queue:
    return Queue("scans", connection=redis or get_redis())


if __name__ == "__main__":
    redis = get_redis()
    queue = get_queue(redis)
    log.info("worker.starting", queues=["scans"])
    Worker([queue], connection=redis).work()
