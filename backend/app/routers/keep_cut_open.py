from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import uuid4
import asyncpg

from app.db import get_db
from app.schemas import (
    StartGameResponse, DecisionRequest, DecisionResponse,
    ItemResponse, StartGameRequest
)
from app.queries import (
    get_random_items,   # we'll create this: fetch N random distinct items by edition
    create_open_session,
    get_open_session,
    update_open_session_decision,
    get_session_items_with_details,
    insert_vote,
    mark_session_complete
)
from app.limiter import limiter

router = APIRouter(prefix="/keep-cut/open", tags=["keep-cut-open"])

@router.post("/start")
@limiter.limit("10/minute")
async def start_open_game(
    req: StartGameRequest,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    # Fetch 8 random items
    items = await get_random_items(conn, req.edition, 8)
    if len(items) < 8:
        raise HTTPException(status_code=400, detail="Not enough items in this edition")
    
    session_id = uuid4()
    item_ids = [item["id"] for item in items]
    await create_open_session(conn, session_id, req.edition, item_ids)
    
    # Convert items to response format
    item_list = [ItemResponse(id=item["id"], name=item["name"], image_url=item["image_url"], edition=item["edition"]) for item in items]
    
    return {
        "session_id": session_id,
        "items": [item.model_dump() for item in item_list],
        "remaining": 8
    }

@router.post("/decide", response_model=DecisionResponse)
@limiter.limit("15/minute")
async def decide_open_game(
    req: DecisionRequest,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    session = await get_open_session(conn, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if item belongs to this session's item_ids
    if req.item_id not in session["item_ids"]:
        raise HTTPException(status_code=400, detail="Item not part of this game")
    
    # Check if this item has already been voted for this session
    existing_vote = await conn.fetchrow(
        "SELECT 1 FROM votes WHERE session_id = $1 AND item_id = $2",
        req.session_id, req.item_id
    )
    if existing_vote:
        raise HTTPException(status_code=400, detail="Item already decided")

    # But we can also check counts.
    if session["remaining"] <= 0:
        raise HTTPException(status_code=400, detail="Game already completed")
    
    # Insert vote
    await insert_vote(conn, req.session_id, req.item_id, session["edition"], req.action)
    
    # Update session counters
    updated = await update_open_session_decision(conn, req.session_id, req.item_id, req.action)
    remaining = updated["remaining"]
    kept_count = updated["kept_count"]
    cut_count = updated["cut_count"]
    
    # Check early termination
    if kept_count == 4 or cut_count == 4:
        # Auto\u2011assign remaining items (those not yet voted)
        # Get all voted item ids from votes table
        voted_rows = await conn.fetch("SELECT item_id FROM votes WHERE session_id = $1", req.session_id)
        voted_ids = [row["item_id"] for row in voted_rows]
        remaining_item_ids = [it for it in session["item_ids"] if it not in voted_ids]
        
        opposite = "cut" if kept_count == 4 else "keep"
        for it_id in remaining_item_ids:
            await insert_vote(conn, req.session_id, it_id, session["edition"], opposite)
        
        await mark_session_complete(conn, req.session_id)
        
        # Fetch final kept and cut items with details
        kept_items_dict, cut_items_dict = await get_session_items_with_details(conn, req.session_id)
        kept_items = [ItemResponse(**item) for item in kept_items_dict]
        cut_items = [ItemResponse(**item) for item in cut_items_dict]
        
        return DecisionResponse(
            session_id=req.session_id,
            round_complete=True,
            remaining=0,
            next_item=None,
            kept_items=kept_items,
            cut_items=cut_items
        )
    
    # If game not finished and remaining == 0 (all 8 decisions made without 4/4)
    if remaining == 0:
        await mark_session_complete(conn, req.session_id)
        kept_items_dict, cut_items_dict = await get_session_items_with_details(conn, req.session_id)
        kept_items = [ItemResponse(**item) for item in kept_items_dict]
        cut_items = [ItemResponse(**item) for item in cut_items_dict]
        return DecisionResponse(
            session_id=req.session_id,
            round_complete=True,
            remaining=0,
            next_item=None,
            kept_items=kept_items,
            cut_items=cut_items
        )
    
    # Game continues, but we don't return a next_item \u2013 UI shows all items.
    # For simplicity, we can return round_complete=False and remaining.
    # The frontend will manage which items are still undecided.
    return DecisionResponse(
        session_id=req.session_id,
        round_complete=False,
        remaining=remaining,
        next_item=None,
        kept_items=None,
        cut_items=None
    )