import pytest
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
async def test_get_leaderboard_kept(client: AsyncClient):
    # Send 11 requests (limit is 10 per minute)
    responses = []
    for _ in range(35):
        resp = await client.get("/votes/leaderboard/kept?edition=movies")
        responses.append(resp)
        # small delay to avoid overwhelming the test client, but not necessary
        await asyncio.sleep(0.01)

    # First 30 should be 200 OK, the 31th should be 429
    assert all(r.status_code == 200 for r in responses[:30])
    assert responses[30].status_code == 429
    assert "Rate limit exceeded" in responses[30].text

@pytest.mark.asyncio
async def test_start_game_rate_limit(client: AsyncClient):
    # Send 11 requests (limit is 10 per minute)
    responses = []
    for _ in range(11):
        resp = await client.post("/keep-cut/start", json={"edition": "anime"})
        responses.append(resp)
        # small delay to avoid overwhelming the test client, but not necessary
        await asyncio.sleep(0.01)

    # First 10 should be 200 OK, the 11th should be 429
    assert all(r.status_code == 200 for r in responses[:10])
    assert responses[10].status_code == 429
    assert "Rate limit exceeded" in responses[10].text

@pytest.mark.asyncio
async def test_decide_rate_limit_per_session(client: AsyncClient):
    # Start a game to get session_id
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]
    first_item = start.json()["item"]

    responses = []
    for _ in range(21):
        resp = await client.post("/keep-cut/decide", json={
            "session_id": session_id,
            "item_id": first_item["id"],
            "action": "keep"
        })
        responses.append(resp)
        await asyncio.sleep(0.01)

    assert all(r.status_code == 200 for r in responses[:15])
    assert responses[15].status_code == 429