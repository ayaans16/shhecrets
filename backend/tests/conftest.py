import fakeredis.aioredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.mongo_client import get_db
from app.core.redis_client import get_redis
from app.main import create_app


@pytest_asyncio.fixture
async def fake_redis():
    # A real Redis (via fakeredis's in-memory server) rather than mocking
    # individual calls - that matters here specifically because
    # test_read_once.py needs GETDEL's real atomicity semantics, not a
    # mock that would happily let two "concurrent" GETDELs both succeed.
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def fake_mongo_db():
    # Same reasoning as fake_redis: a real (in-memory) Mongo rather than
    # mocking insert_one/update_one calls, so tests exercise actual
    # document reads/writes instead of asserting "was this method called."
    # Without this override, tests hit the real motor client from
    # core/mongo_client.py and burn ~30s per test waiting on a Mongo
    # connection timeout before the service layer's try/except swallows it.
    client = AsyncMongoMockClient()
    yield client["test_shhecrets"]


@pytest_asyncio.fixture
async def client(fake_redis, fake_mongo_db):
    app = create_app()

    async def _override_get_redis():
        return fake_redis

    async def _override_get_db():
        return fake_mongo_db

    app.dependency_overrides[get_redis] = _override_get_redis
    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
