import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_start_game(client: AsyncClient):
    response = await client.post("/keep-cut/start", json={"edition": "anime"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "item" in data
    assert data["remaining"] == 8
    assert data["item"]["edition"] == "anime"


@pytest.mark.asyncio
async def test_start_game_insufficient_items(client: AsyncClient):
    # Try a category with less than 8 items (e.g., tv_shows only 2 in sample)
    response = await client.post("/keep-cut/start", json={"edition": "tv_shows"})
    assert response.status_code == 400
    assert "Need at least 8" in response.text


@pytest.mark.asyncio
async def test_make_decision_keep(client: AsyncClient):
    # Start a game
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]
    item_id = start.json()["item"]["id"]
    
    # Make a keep decision
    response = await client.post("/keep-cut/decide", json={
        "session_id": session_id,
        "item_id": item_id,
        "action": "keep"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["round_complete"] is False
    assert data["remaining"] == 7
    assert data["next_item"] is not None


@pytest.mark.asyncio
async def test_make_decision_cut(client: AsyncClient):
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]
    item_id = start.json()["item"]["id"]
    
    response = await client.post("/keep-cut/decide", json={
        "session_id": session_id,
        "item_id": item_id,
        "action": "cut"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["round_complete"] is False
    assert data["remaining"] == 7


@pytest.mark.asyncio
async def test_complete_full_game(client: AsyncClient):
    # Start anime game (8 items)
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]
    first_item = start.json()["item"]
    
    # We'll play 8 rounds, recording decisions
    # For simplicity, keep all items
    current_decision = await client.post("/keep-cut/decide", json={
        "session_id": session_id,
        "item_id": first_item["id"],
        "action": "keep"
    })
    current_data = current_decision.json()
    
    # Perform remaining 7 decisions
    for _ in range(7):
        next_item = current_data["next_item"]
        response = await client.post("/keep-cut/decide", json={
            "session_id": session_id,
            "item_id": next_item["id"],
            "action": "keep"
        })
        current_data = response.json()
        if current_data["round_complete"]:
            break
    
    assert current_data["round_complete"] is True
    assert len(current_data["kept_items"]) == 8
    assert len(current_data["cut_items"]) == 0


@pytest.mark.asyncio
async def test_get_session_status(client: AsyncClient):
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]
    item_id = start.json()["item"]["id"]
    await client.post("/keep-cut/decide", json={
        "session_id": session_id,
        "item_id": item_id,
        "action": "keep"
    })
    
    status = await client.get(f"/keep-cut/session/{session_id}")
    assert status.status_code == 200
    data = status.json()
    assert data["remaining"] == 7
    assert len(data["kept_items"]) == 1
    assert len(data["cut_items"]) == 0


@pytest.mark.asyncio
async def test_session_not_found(client: AsyncClient):
    response = await client.get("/keep-cut/session/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404