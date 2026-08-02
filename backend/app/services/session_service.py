import secrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from fastapi import HTTPException, status

from app.config import get_settings

# 32 bytes = 256 bits of entropy, the same strength as an AES-256 key.
# token_urlsafe base64-encodes that into a 43-character URL-safe string -
# long and random enough that guessing a live session ID by brute force
# is infeasible even without rate limiting (rate limiting is there for
# defense-in-depth, not because this alone is guessable).
_SESSION_ID_BYTES = 32


def _meta_key(session_id: str) -> str:
    return f"sess:{session_id}:meta"


def _secret_key(session_id: str) -> str:
    return f"sess:{session_id}:secret"


async def create_session(redis_client: redis.Redis) -> tuple[str, datetime]:
    settings = get_settings()

    # secrets.token_urlsafe uses the OS CSPRNG. Never use the `random`
    # module for this - its output is predictable enough to reconstruct,
    # and this ID is the only thing standing between an attacker and
    # someone else's live secret.
    session_id = secrets.token_urlsafe(_SESSION_ID_BYTES)

    ttl = settings.session_ttl_seconds
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    # The meta key is the authoritative "creation clock": its TTL is what
    # makes the session die on schedule even if the secret is never
    # submitted. Its value is never read - existence + remaining TTL is
    # all set_secret() below needs.
    await redis_client.set(_meta_key(session_id), "1", ex=ttl)

    return session_id, expires_at


async def set_secret(redis_client: redis.Redis, session_id: str, content: str) -> None:
    remaining_ttl = await redis_client.ttl(_meta_key(session_id))
    if remaining_ttl < 0:
        # redis-py's ttl() returns -2 (key doesn't exist) or -1 (exists,
        # no expiry - which we never set). Either way there's no valid
        # session to attach a secret to.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired.",
        )

    # Capped at whatever's left of the *original* session lifetime, not a
    # fresh full TTL - submitting the secret late doesn't extend the
    # session past the 10 minutes (or configured TTL) promised at creation.
    await redis_client.set(_secret_key(session_id), content, ex=remaining_ttl)


async def read_and_burn(redis_client: redis.Redis, session_id: str) -> str:
    # GETDEL is a single atomic Redis command - it fetches and deletes in
    # one server-side step, so two concurrent reads can't both get the
    # content. Whichever request loses the race sees None, which is
    # indistinguishable from "expired" or "never existed" by design (we
    # don't want to leak which case it was).
    content = await redis_client.getdel(_secret_key(session_id))
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found, already read, or expired.",
        )
    return content
