from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import List, Optional

@dataclass
class Item:
    id: int
    name: str
    image_url: Optional[str]
    edition: str          # 'anime', 'movies', 'tv_shows'
    tmdb_id: Optional[int] = None
    anilist_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class GameSession:
    id: UUID
    edition: str
    remaining: int
    shown_ids: List[int]      # items already presented
    kept_ids: List[int]
    cut_ids: List[int]
    created_at: datetime
    updated_at: datetime


@dataclass
class Vote:
    id: int
    session_id: UUID
    item_id: int
    edition: str
    decision: str             # 'keep' or 'cut'
    voted_at: datetime


# Helper to convert DB row (asyncpg record) to dataclass
def item_from_row(row) -> Item:
    return Item(
        id=row["id"],
        name=row["name"],
        image_url=row["image_url"],
        edition=row["edition"],
        tmdb_id=row.get("tmdb_id"),
        anilist_id=row.get("anilist_id"),
        created_at=row.get("created_at")
    )