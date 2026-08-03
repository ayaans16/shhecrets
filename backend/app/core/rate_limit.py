import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings
from app.core.redis_client import get_redis


def _client_ip(request: Request) -> str:
    # In production this app sits behind Cloudflare -> Caddy, so
    # request.client.host would be Caddy's own container IP, not the
    # caller's - every request would land in the same rate-limit bucket.
    # CF-Connecting-IP is set by Cloudflare itself from its edge
    # connection to the visitor, and Cloudflare strips any
    # client-supplied value with that name before setting its own - so a
    # client can't spoof it to dodge the limit or frame another IP.
    # Trusting it is safe specifically because Caddy/the backend are only
    # ever reachable through Cloudflare (nothing else can reach them -
    # see docker-compose.prod.yml, which publishes no other ports).
    #
    # Locally (no Cloudflare in front), the header is simply absent and
    # this falls back to the direct TCP peer.
    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip
    return request.client.host if request.client else "unknown"


async def _enforce(request: Request, redis_client: redis.Redis, scope: str, limit: tuple[int, int]) -> None:
    max_requests, window_seconds = limit

    key = f"ratelimit:{scope}:{_client_ip(request)}"

    # Fixed-window counter: INCR the key, set its TTL only on the first
    # hit in the window. A few bytes in Redis and one round trip per
    # request.
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
