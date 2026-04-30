import pytest
from httpx import AsyncClient
from app.queries import insert_vote


@pytest.mark.asyncio
async def test_leaderboard_kept(client: AsyncClient, db_connection):
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]
    
    await insert_vote(db_connection, session_id, 1, "anime", "keep")
    await insert_vote(db_connection, session_id, 2, "anime", "keep")
    await insert_vote(db_connection, session_id, 1, "anime", "keep")
    
    response = await client.get("/votes/leaderboard/kept?edition=anime&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    # Item 1 should have keep_count 2
    for item in data:
        if item["item_id"] == 1:
            assert item["keep_count"] == 2
        if item["item_id"] == 2:
            assert item["keep_count"] == 1


@pytest.mark.asyncio
async def test_leaderboard_cut(client: AsyncClient, db_connection):
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]

    await insert_vote(db_connection, session_id, 3, "anime", "cut")
    await insert_vote(db_connection, session_id, 3, "anime", "cut")
    await insert_vote(db_connection, session_id, 4, "anime", "cut")
    
    response = await client.get("/votes/leaderboard/cut?edition=anime&limit=5")
    assert response.status_code == 200
    data = response.json()
    for item in data:
        if item["item_id"] == 3:
            assert item["cut_count"] == 2


@pytest.mark.asyncio
async def test_edition_stats(client: AsyncClient, db_connection):
    start = await client.post("/keep-cut/start", json={"edition": "anime"})
    session_id = start.json()["session_id"]

    await insert_vote(db_connection, session_id, 1, "anime", "keep")
    await insert_vote(db_connection, session_id, 2, "anime", "cut")
    await insert_vote(db_connection, session_id, 3, "anime", "keep")
    
    response = await client.get("/votes/stats/edition/anime")
    assert response.status_code == 200
    data = response.json()
    assert data["total_keeps"] >= 2
    assert data["total_cuts"] >= 1
    assert data["total_votes"] >= 3