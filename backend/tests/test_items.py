import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_items_all(client: AsyncClient):
    response = await client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 12  # from sample data


@pytest.mark.asyncio
async def test_list_items_filter_anime(client: AsyncClient):
    response = await client.get("/items/?edition=anime")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 8  # we inserted 8 anime


@pytest.mark.asyncio
async def test_list_items_pagination(client: AsyncClient):
    response = await client.get("/items/?limit=5&offset=0")
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_get_item_by_id(client: AsyncClient):
    # First get an item ID
    resp = await client.get("/items/?edition=anime&limit=1")
    item = resp.json()[0]
    item_id = item["id"]
    
    response = await client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["edition"] == "anime"


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    response = await client.get("/items/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_count_items_anime(client: AsyncClient):
    response = await client.get("/items/count/anime")
    assert response.status_code == 200
    assert response.json() == 8