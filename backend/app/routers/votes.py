from fastapi import APIRouter, Depends, Query, Request
from typing import List
import asyncpg

from app.db import get_db
from app.queries import top_kept_items, top_cut_items
from app.schemas import LeaderboardEntry
from app.limiter import limiter

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("/leaderboard/kept", response_model=List[LeaderboardEntry])
@limiter.limit("30/minute")
async def get_kept_leaderboard(
    request: Request,
    edition: str = Query(..., description="Edition: anime, movies, tv_shows"),
    limit: int = Query(10, ge=1, le=50),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Returns the top N most kept items for a given edition.
    """
    results = await top_kept_items(conn, edition, limit)
    return [
        LeaderboardEntry(
            item_id=row["id"],
            name=row["name"],
            image_url=row["image_url"],
            keep_count=row["keep_count"],
            cut_count=0  # not used in this endpoint
        )
        for row in results
    ]


@router.get("/leaderboard/cut", response_model=List[LeaderboardEntry])
async def get_cut_leaderboard(
    request: Request,
    edition: str = Query(..., description="Edition: anime, movies, tv_shows"),
    limit: int = Query(10, ge=1, le=50),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Returns the top N most cut items for a given edition.
    """
    results = await top_cut_items(conn, edition, limit)
    return [
        LeaderboardEntry(
            item_id=row["id"],
            name=row["name"],
            image_url=row["image_url"],
            keep_count=0,
            cut_count=row["cut_count"]
        )
        for row in results
    ]


@router.get("/stats/edition/{edition}")
async def get_edition_stats(
    edition: str,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Returns aggregated vote statistics for a specific edition:
    - total_keeps, total_cuts, total_votes
    """
    row = await conn.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE decision = 'keep') AS total_keeps,
            COUNT(*) FILTER (WHERE decision = 'cut') AS total_cuts,
            COUNT(*) AS total_votes
        FROM votes
        WHERE edition = $1
    """, edition)
    if not row:
        return {"edition": edition, "total_keeps": 0, "total_cuts": 0, "total_votes": 0}
    return {
        "edition": edition,
        "total_keeps": row["total_keeps"],
        "total_cuts": row["total_cuts"],
        "total_votes": row["total_votes"]
    }