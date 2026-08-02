from app.services import session_service


class _BrokenCollection:
    async def insert_one(self, *args, **kwargs):
        raise RuntimeError("mongo is down")

    async def update_one(self, *args, **kwargs):
        raise RuntimeError("mongo is down")


class _BrokenMongoDb:
    def __getitem__(self, name):
        return _BrokenCollection()


async def test_create_session_writes_metadata_without_secret_or_raw_ip(client, fake_mongo_db):
    resp = await client.post("/sessions")
    session_id = resp.json()["session_id"]

    doc = await fake_mongo_db["sessions"].find_one({"session_id": session_id})
    assert doc is not None
    assert doc["session_id"] == session_id
    assert doc["read"] is False
    assert doc["read_count"] == 0
    assert doc["hashed_ip"] is not None
    assert doc["hashed_ip"] != "testclient"  # never the raw peer address

    # Structural guarantee: Mongo's view of a session never grows a
    # "content"/"key" field. Asserting the exact key set means a future
    # change that accidentally stores secret content here fails loudly.
    assert set(doc.keys()) == {
        "_id",
        "session_id",
        "created_at",
        "expires_at",
        "read",
        "read_count",
        "read_at",
        "hashed_ip",
    }


async def test_successful_read_marks_metadata_as_read(client, fake_mongo_db):
    create_resp = await client.post("/sessions")
    session_id = create_resp.json()["session_id"]
    await client.put(f"/sessions/{session_id}/secret", json={"content": "x"})

    read_resp = await client.get(f"/sessions/{session_id}")
    assert read_resp.status_code == 200

    doc = await fake_mongo_db["sessions"].find_one({"session_id": session_id})
    assert doc["read"] is True
    assert doc["read_count"] == 1
    assert doc["read_at"] is not None


async def test_failed_read_attempts_still_increment_read_count(client, fake_mongo_db):
    create_resp = await client.post("/sessions")
    session_id = create_resp.json()["session_id"]
    await client.put(f"/sessions/{session_id}/secret", json={"content": "x"})

    await client.get(f"/sessions/{session_id}")  # succeeds, burns the secret
    await client.get(f"/sessions/{session_id}")  # fails - already burned
    await client.get(f"/sessions/{session_id}")  # fails again

    doc = await fake_mongo_db["sessions"].find_one({"session_id": session_id})
    # One success plus two failed attempts against the same (now-burned)
    # session - a pattern worth flagging for abuse tracking even though
    # the secret itself is already safely gone.
    assert doc["read_count"] == 3
    assert doc["read"] is True


async def test_create_session_succeeds_even_if_mongo_is_down(fake_redis):
    session_id, expires_at = await session_service.create_session(
        fake_redis, _BrokenMongoDb(), "1.2.3.4"
    )
    assert session_id
    assert expires_at is not None


async def test_read_and_burn_succeeds_even_if_mongo_is_down(fake_redis):
    session_id, _ = await session_service.create_session(fake_redis, _BrokenMongoDb(), "1.2.3.4")
    await session_service.set_secret(fake_redis, session_id, "still-works")

    content = await session_service.read_and_burn(fake_redis, _BrokenMongoDb(), session_id)
    assert content == "still-works"
