from functools import lru_cache

import redis.asyncio as redis

from app.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    # One client (i.e. one connection pool) per process, reused across
    # requests. redis-py's async client is safe to share this way, and
    # reusing the pool matters more once this runs as a Lambda that gets
    # frozen/thawed between invocations - we don't want to open a fresh
    # TCP connection to Redis on every single request.
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> redis.Redis:
    """FastAPI dependency: `redis_client: redis.Redis = Depends(get_redis)`."""
    return get_redis_client()
