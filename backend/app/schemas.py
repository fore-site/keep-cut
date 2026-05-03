from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional

# ----- Request/Response schemas -----

class ItemResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    edition: str  # 'anime', 'movies', 'tv_shows'


class StartGameRequest(BaseModel):
    edition: str = Field(..., pattern="^(anime|movies|tv_shows)$")


class StartGameResponse(BaseModel):
    session_id: UUID
    item: ItemResponse
    remaining: int  # should be 8 initially


class DecisionRequest(BaseModel):
    session_id: UUID
    item_id: int
    action: str = Field(..., pattern="^(keep|cut)$")


class DecisionResponse(BaseModel):
    session_id: UUID
    round_complete: bool  # True if game finished after this decision
    remaining: int
    next_item: Optional[ItemResponse] = None
    kept_items: Optional[List[ItemResponse]] = None
    cut_items: Optional[List[ItemResponse]] = None
    # If round_complete == True, kept_items and cut_items are populated


class SessionStatusResponse(BaseModel):
    session_id: UUID
    edition: str
    remaining: int
    kept_items: List[ItemResponse]
    cut_items: List[ItemResponse]


class ResultsResponse(BaseModel):
    session_id: UUID
    edition: str
    kept_items: List[ItemResponse]
    cut_items: List[ItemResponse]


class VotePayload(BaseModel):
    session_id: UUID
    item_id: int
    decision: str


class LeaderboardEntry(BaseModel):
    item_id: int
    name: str
    image_url: Optional[str]
    keep_count: int
    cut_count: int
