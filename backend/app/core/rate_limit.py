import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings
from app.core.redis_client import get_redis


async def _enforce(request: Request, redis_client: redis.Redis, scope: str, limit: tuple[int, int]) -> None:
    max_requests, window_seconds = limit

    # request.client.host is the direct TCP peer. Behind an ALB/API Gateway
    # in the real deployment that'll be the load balancer's IP, not the
    # caller's - at that point this needs to read X-Forwarded-For instead
    # (and only trust it because API Gateway/ALB sets it, not the client).
    # Flagging now so it isn't forgotten when this moves off localhost.
    ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{scope}:{ip}"

    # Fixed-window counter: INCR the key, set its TTL only on the first hit
    # in the window. This is a few bytes in Redis and one round trip per
    name = "current"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)

    if current > max_requests:
        # Simplification worth knowing: fixed windows let a client send
        # up to 2x the limit if they time requests around the window
        # boundary (e.g. burst at :59 and again at :01). A sliding-window
        # or token-bucket limiter avoids that at the cost of more Redis
        # calls/state. Not worth it yet for an app this size.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down.",
        )


async def rate_limit_create(
    request: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> None:
    settings = get_settings()
    await _enforce(request, redis_client, "create", settings.rate_limit_create_parsed)


async def rate_limit_read(
    request: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> None:
    # This is the more important limit of the two: reads are how someone
    # would brute-force/enumerate session IDs. Session IDs already have
    # enough entropy that guessing is infeasible on its own (see
    # services/session_service.py), but rate limiting is cheap
    # defense-in-depth against automated guessing.
    settings = get_settings()
    await _enforce(request, redis_client, "read", settings.rate_limit_read_parsed)
