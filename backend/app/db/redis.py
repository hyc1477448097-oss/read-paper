from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.Redis | None = None

DEFAULT_TTL = 3600  # 1 hour


async def init_redis() -> None:
    global _pool
    _pool = aioredis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def get_redis() -> aioredis.Redis:
    if _pool is None:
        raise RuntimeError("Redis not initialised – call init_redis() first")
    return _pool


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    val = await r.get(key)
    if val is None:
        return None
    return json.loads(val)


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    r = get_redis()
    await r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)
