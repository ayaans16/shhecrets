from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings


@lru_cache
def get_mongo_client() -> AsyncIOMotorClient:
    # Same reasoning as get_redis_client(): one client/connection pool per
    # process, reused across requests rather than reconnecting each time.
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongo_url)


async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency: `db: AsyncIOMotorDatabase = Depends(get_db)`."""
    settings = get_settings()
    return get_mongo_client()[settings.mongo_db_name]
