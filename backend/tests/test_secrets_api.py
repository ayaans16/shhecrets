async def test_create_submit_read_flow(client):
    create_resp = await client.post("/sessions")
    assert create_resp.status_code == 200
    body = create_resp.json()
    session_id = body["session_id"]
    assert "expires_at" in body

    submit_resp = await client.put(
        f"/sessions/{session_id}/secret", json={"content": "super-secret-value"}
    )
    assert submit_resp.status_code == 204

    read_resp = await client.get(f"/sessions/{session_id}")
    assert read_resp.status_code == 200
    assert read_resp.json()["content"] == "super-secret-value"


async def test_read_after_burn_returns_404(client):
    create_resp = await client.post("/sessions")
    session_id = create_resp.json()["session_id"]
    await client.put(f"/sessions/{session_id}/secret", json={"content": "x"})

    first = await client.get(f"/sessions/{session_id}")
    assert first.status_code == 200

    second = await client.get(f"/sessions/{session_id}")
    assert second.status_code == 404


async def test_read_unknown_session_returns_404(client):
    resp = await client.get("/sessions/does-not-exist")
    assert resp.status_code == 404


async def test_submit_secret_to_unknown_session_returns_404(client):
    resp = await client.put("/sessions/does-not-exist/secret", json={"content": "x"})
    assert resp.status_code == 404


async def test_oversized_secret_rejected_without_leaking_content(client):
    create_resp = await client.post("/sessions")
    session_id = create_resp.json()["session_id"]

    huge_content = "x" * 70_000
    resp = await client.put(f"/sessions/{session_id}/secret", json={"content": huge_content})

    assert resp.status_code == 422
    # The point of the custom validation handler in main.py: an invalid
    # (here, oversized) secret must never be echoed back in the error body.
    assert huge_content not in resp.text
