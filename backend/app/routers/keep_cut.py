import logging
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.db import get_db
from app.schemas import (
    StartGameRequest,
    StartGameResponse,
    DecisionRequest,
    DecisionResponse,
    SessionStatusResponse,
    ItemResponse
)
from app.queries import (
    get_random_item_by_edition,
    get_random_item_excluding,
    get_item_by_id,
    create_session,
    get_session,
    update_session_decision,
    delete_session,
    get_session_items_with_details,
    insert_vote,
    count_items_by_edition
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keep-cut", tags=["keep-cut"])


@router.post("/start", response_model=StartGameResponse)
async def start_game(
    req: StartGameRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Start a new game session.
    - Creates a session with 8 remaining choices.
    - Returns the first random item.
    """
    # Verify there are enough items for the edition
    item_count = await count_items_by_edition(conn, req.edition)
    if item_count < 8:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough items in edition '{req.edition}'. Need at least 8, found {item_count}."
        )

    # Pick first random item
    first_item = await get_random_item_by_edition(conn, req.edition)
    if not first_item:
        raise HTTPException(status_code=404, detail="No items found for this edition")

    # Create session
    session_id = uuid4()
    session = await create_session(conn, session_id, req.edition)

    # Convert to response
    return StartGameResponse(
        session_id=session["id"],
        item=ItemResponse(
            id=first_item["id"],
            name=first_item["name"],
            image_url=first_item["image_url"],
            edition=first_item["edition"]
        ),
        remaining=session["remaining"]
    )


@router.post("/decide", response_model=DecisionResponse)
async def make_decision(
    req: DecisionRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Process a keep/cut decision.
    - Updates the session (append to kept/cut arrays, shown_ids, decrement remaining).
    - Logs a vote in the analytics table.
    - If remaining becomes 0, returns the final lists and deletes the session.
    - Otherwise returns the next random item.
    """
    # Check if session exists
    session = await get_session(conn, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["remaining"] <= 0:
        raise HTTPException(status_code=400, detail="Game already completed")

    # Ensure the item belongs to the same edition (optional security check)
    item = await get_item_by_id(conn, req.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["edition"] != session["edition"]:
        raise HTTPException(status_code=400, detail="Item edition mismatch")

    # Record the decision in the session
    if req.action == "cut" or req.action == "keep":
        updated = await update_session_decision(conn, req.session_id, req.item_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Log vote for analytics (asynchronously; no need to wait, but we do for simplicity)
    await insert_vote(conn, req.session_id, req.item_id, session["edition"], req.action)

    remaining = updated["remaining"]

    # If game is not finished, fetch next item (not in shown_ids)
    if remaining > 0:
        shown_ids = updated["shown_ids"]
        next_item = await get_random_item_excluding(conn, session["edition"], shown_ids)
        if not next_item:
            # Fallback: should not happen if database has enough items
            raise HTTPException(status_code=500, detail="Failed to fetch next item")

        return DecisionResponse(
            session_id=req.session_id,
            round_complete=False,
            remaining=remaining,
            next_item=ItemResponse(
                id=next_item["id"],
                name=next_item["name"],
                image_url=next_item["image_url"],
                edition=next_item["edition"]
            ),
            kept_items=None,
            cut_items=None
        )

    # Game finished: get final kept/cut from votes
    kept_items_dict, cut_items_dict = await get_session_items_with_details(conn, req.session_id)
    kept_items = [ItemResponse(**item) for item in kept_items_dict]
    cut_items = [ItemResponse(**item) for item in cut_items_dict]

    # Delete the session (cleanup)
    await delete_session(conn, req.session_id)

    return DecisionResponse(
        session_id=req.session_id,
        round_complete=True,
        remaining=0,
        next_item=None,
        kept_items=kept_items,
        cut_items=cut_items
    )


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: UUID,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get current status of an active session (resume or inspect).
    Includes kept/cut lists so far, remaining count, and the items themselves.
    """
    session = await get_session(conn, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["remaining"] == 0:
        raise HTTPException(status_code=400, detail="Game already completed (session should have been cleaned)")

    # Fetch full item details for kept and cut IDs
    kept_items_dict, cut_items_dict = await get_session_items_with_details(conn, session_id)
    kept_items = [ItemResponse(**item) for item in kept_items_dict]
    cut_items = [ItemResponse(**item) for item in cut_items_dict]


    # Note: We don't return the current / next item because the game is sequential,
    # and the next item would be determined only after the next decision.
    # The frontend can call this endpoint to display the user's progress.
    return SessionStatusResponse(
        session_id=session["id"],
        edition=session["edition"],
        remaining=session["remaining"],
        kept_items=kept_items,
        cut_items=cut_items
    )