import fakeredis.aioredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

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
async def client(fake_redis):
    app = create_app()

    async def _override_get_redis():
        return fake_redis

    app.dependency_overrides[get_redis] = _override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
