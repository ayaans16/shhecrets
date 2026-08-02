import hashlib

from app.config import get_settings


def hash_ip(ip: str) -> str:
    # SHA-256 salted with a server-side pepper. We only need this value
    # to correlate "same sender created/read multiple sessions" for abuse
    # tracking - we specifically must NOT be able to recover the actual
    # IP from what's stored in Mongo (that's the whole point of hashing
    # it instead of storing it raw).
    settings = get_settings()
    return hashlib.sha256(f"{settings.ip_hash_pepper}:{ip}".encode()).hexdigest()
