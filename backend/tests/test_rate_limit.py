from app.config import get_settings


async def test_requests_are_bucketed_by_cf_connecting_ip(client):
    # Regression test for the fix in core/rate_limit.py: without reading
    # CF-Connecting-IP, every request in this test suite (and in
    # production, every request behind Caddy) would share one bucket
    # keyed off the same proxy IP, making the limit meaningless.
    max_requests, _ = get_settings().rate_limit_read_parsed
    headers_a = {"CF-Connecting-IP": "1.1.1.1"}
    headers_b = {"CF-Connecting-IP": "2.2.2.2"}

    responses_a = [
        await client.get("/sessions/does-not-exist", headers=headers_a)
        for _ in range(max_requests + 1)
    ]
    assert responses_a[-1].status_code == 429

    # A different caller (different CF-Connecting-IP) has its own,
    # untouched budget - proves buckets are keyed by that header rather
    # than colliding on the shared test-client peer address.
    response_b = await client.get("/sessions/does-not-exist", headers=headers_b)
    assert response_b.status_code == 404
