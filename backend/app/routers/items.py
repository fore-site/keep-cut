from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
import asyncpg

from app.db import get_db
from app.queries import (
    get_item_by_id,
    get_items_by_edition,
    count_items_by_edition
)
from app.schemas import ItemResponse

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=List[ItemResponse])
async def list_items(
    request: Request,
    edition: Optional[str] = Query(None, description="Filter by edition: anime, movies, tv_shows"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    List items (anime, movies, TV shows) with optional edition filter and pagination.
    """
    items = await get_items_by_edition(conn, edition, limit, offset)
    return [ItemResponse(**dict(item)) for item in items]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get a single item by its ID.
    """
    item = await get_item_by_id(conn, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**dict(item))


@router.get("/count/{edition}", response_model=int)
async def count_items(
    edition: str,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get the total number of items for a specific edition.
    """
    count = await count_items_by_edition(conn, edition)
    return count