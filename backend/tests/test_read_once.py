import asyncio


async def test_concurrent_reads_exactly_one_succeeds(client):
    create_resp = await client.post("/sessions")
    session_id = create_resp.json()["session_id"]
    await client.put(f"/sessions/{session_id}/secret", json={"content": "race-me"})

    # Fire two reads at once rather than sequentially - this is the case
    # that a naive "GET then DELETE" (two round trips) would get wrong:
    # both requests could read the value before either one deletes it.
    # GETDEL closes that window by making read-and-delete a single atomic
    # command.
    responses = await asyncio.gather(
        client.get(f"/sessions/{session_id}"),
        client.get(f"/sessions/{session_id}"),
    )

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 404]

    winner = next(r for r in responses if r.status_code == 200)
    assert winner.json()["content"] == "race-me"


async def test_many_concurrent_reads_exactly_one_succeeds(client):
    create_resp = await client.post("/sessions")
    session_id = create_resp.json()["session_id"]
    await client.put(f"/sessions/{session_id}/secret", json={"content": "race-me"})

    # A wider fan-out of the same race, to make it harder for the
    # assertion to pass by luck if atomicity were ever accidentally broken.
    responses = await asyncio.gather(
        *[client.get(f"/sessions/{session_id}") for _ in range(20)]
    )

    successes = [r for r in responses if r.status_code == 200]
    assert len(successes) == 1
    assert successes[0].json()["content"] == "race-me"
