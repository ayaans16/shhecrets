from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_rate(raw: str) -> tuple[int, int]:
    """'<max requests>/<window seconds>' -> (max, window)."""
    max_requests, window_seconds = raw.split("/")
    return int(max_requests), int(window_seconds)


class Settings(BaseSettings):
    # pydantic-settings reads these straight from the process environment
    # (with .env as a local-dev fallback). No separate config-file parser
    # needed, and it's a direct match for how Lambda/ECS inject env vars in
    # every deploy target we're aiming for later.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    redis_url: str = "redis://localhost:6379/0"

    # Sessions self-destruct after this long even if never read. Redis TTL
    # enforces this natively (see core/redis_client.py) so there's no cron
    # job or sweep process needed to clean up abandoned sessions.
    session_ttl_seconds: int = 600

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "shhecrets"

    # Pepper mixed into the IP hash (see core/security.py) so the stored
    # hash can't be reversed via a rainbow table of common IPs. This is a
    # throwaway default for local dev only - a real deploy must set this
    # from Secrets Manager (e.g. `openssl rand -hex 32`), otherwise the
    # "hashed, not raw" IP protection is mostly theater.
    ip_hash_pepper: str = "local-dev-pepper-do-not-use-in-prod"

    cors_origins: str = "http://localhost:5173"

    rate_limit_create: str = "10/60"
    rate_limit_read: str = "20/60"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def rate_limit_create_parsed(self) -> tuple[int, int]:
        return _parse_rate(self.rate_limit_create)

    @property
    def rate_limit_read_parsed(self) -> tuple[int, int]:
        return _parse_rate(self.rate_limit_read)


@lru_cache
def get_settings() -> Settings:
    # lru_cache makes this a process-wide singleton without needing a global
    # variable or app-startup wiring - every call site just does
    # get_settings() and gets the same parsed instance.
    return Settings()
