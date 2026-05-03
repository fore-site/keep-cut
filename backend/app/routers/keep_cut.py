import logging
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from app.limiter import limiter
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
    get_random_unshown_items,
    mark_session_complete,
    get_session_items_with_details,
    insert_vote,
    count_items_by_edition
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keep-cut", tags=["keep-cut"])


@router.post("/blind/start", response_model=StartGameResponse)
@limiter.limit("10/minute")
async def start_game(
    req: StartGameRequest,
    request: Request,
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


@router.post("/blind/decide", response_model=DecisionResponse)
@limiter.limit("15/minute")
async def make_decision(
    req: DecisionRequest,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Process a keep/cut decision.
    - Updates the session (append to kept/cut arrays, shown_ids, decrement remaining).
    - Logs a vote in the analytics table.
    - If remaining becomes 0, returns the final lists and deletes the session.
    - Otherwise returns the next random item.
    """
    # Check if session is active (completed = false)
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

    if req.action == "cut" or req.action == "keep":
    # Update session (add to shown_ids, increment counter, decrement remaining)
        updated = await update_session_decision(conn, req.session_id, req.item_id, req.action)
        remaining = updated["remaining"]
        kept_count = updated["kept_count"]
        cut_count = updated["cut_count"]
        shown_ids = updated["shown_ids"]
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Log vote for analytics (asynchronously; no need to wait, but we do for simplicity)
    await insert_vote(conn, req.session_id, req.item_id, session["edition"], req.action)

    # Check if game should end early (keep == 4 or cut == 4)
    if kept_count == 4 or cut_count == 4:
        # Determine which category is full
        full_category = 'keep' if kept_count == 4 else 'cut'
        opposite = 'cut' if full_category == 'keep' else 'keep'
        needed = 8 - len(shown_ids)

        if needed > 0:
            remaining_items = await get_random_unshown_items(conn, session["edition"], shown_ids, needed)

            # Auto-vote for each remaining item with the opposite decision
            for item in remaining_items:
                await insert_vote(conn, req.session_id, item["id"], session["edition"], opposite)
                await update_session_decision(conn, req.session_id, item["id"], opposite)

        # After auto‑votes, fetch final kept/cut items
        kept_items_dict, cut_items_dict = await get_session_items_with_details(conn, req.session_id)
        kept_items = [ItemResponse(**item) for item in kept_items_dict]
        cut_items = [ItemResponse(**item) for item in cut_items_dict]

        # Delete session
        await mark_session_complete(conn, req.session_id)

        return DecisionResponse(
            session_id=req.session_id,
            round_complete=True,
            remaining=0,
            next_item=None,
            kept_items=kept_items,
            cut_items=cut_items
        )

    # Otherwise (game continues normally)
    if remaining > 0:
        next_item = await get_random_item_excluding(conn, session["edition"], shown_ids)
        if not next_item:
            raise HTTPException(status_code=500, detail="Failed to fetch next item")
        return DecisionResponse(
            session_id=req.session_id,
            round_complete=False,
            remaining=remaining,
            next_item=ItemResponse(**dict(next_item)),
            kept_items=None,
            cut_items=None
        )

    # If remaining == 0 but neither count reached 4 (should not happen with this logic)
    # Fallback to normal completion (same as before)
    kept_items_dict, cut_items_dict = await get_session_items_with_details(conn, req.session_id)
    kept_items = [ItemResponse(**item) for item in kept_items_dict]
    cut_items = [ItemResponse(**item) for item in cut_items_dict]
    await mark_session_complete(conn, req.session_id)
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
    request: Request,
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