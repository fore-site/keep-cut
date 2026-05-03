import asyncpg
from typing import List, Optional
from uuid import UUID

# =====================================================
# Items
# =====================================================

async def get_random_item_by_edition(
    conn: asyncpg.Connection,
    edition: str
) -> Optional[asyncpg.Record]:
    """Fetch a random item from the specified edition."""
    return await conn.fetchrow("""
        SELECT id, name, image_url, edition
        FROM items
        WHERE edition = $1
        ORDER BY RANDOM()
        LIMIT 1
    """, edition)


async def get_random_item_excluding(
    conn: asyncpg.Connection,
    edition: str,
    excluded_ids: List[int]
) -> Optional[asyncpg.Record]:
    """Fetch a random item not in excluded_ids."""
    return await conn.fetchrow("""
        SELECT id, name, image_url, edition
        FROM items
        WHERE edition = $1
          AND id != ANY($2::int[])
        ORDER BY RANDOM()
        LIMIT 1
    """, edition, excluded_ids)


async def get_item_by_id(
    conn: asyncpg.Connection,
    item_id: int
) -> Optional[asyncpg.Record]:
    """Fetch a single item by its ID."""
    return await conn.fetchrow("""
        SELECT id, name, image_url, edition
        FROM items
        WHERE id = $1
    """, item_id)


async def get_items_by_edition(
    conn: asyncpg.Connection,
    edition: Optional[str],
    limit: int,
    offset: int
) -> List[asyncpg.Record]:
    """Fetch items with optional edition filter and pagination."""
    if edition:
        return await conn.fetch("""
            SELECT id, name, image_url, edition
            FROM items
            WHERE edition = $1
            ORDER BY id
            LIMIT $2 OFFSET $3
        """, edition, limit, offset)
    else:
        return await conn.fetch("""
            SELECT id, name, image_url, edition
            FROM items
            ORDER BY id
            LIMIT $1 OFFSET $2
        """, limit, offset)


async def count_items_by_edition(
    conn: asyncpg.Connection,
    edition: str
) -> int:
    """Return the total number of items in an edition."""
    row = await conn.fetchrow("""
        SELECT COUNT(*) as count
        FROM items
        WHERE edition = $1
    """, edition)
    return row["count"] if row else 0


# =====================================================
# Game Sessions
# =====================================================

async def create_session(
    conn: asyncpg.Connection,
    session_id: UUID,
    edition: str
) -> asyncpg.Record:
    """Create a new game session and return its record."""
    return await conn.fetchrow("""
        INSERT INTO game_sessions (id, edition)
        VALUES ($1, $2)
        RETURNING id, edition, remaining
    """, session_id, edition)


async def get_session(
    conn: asyncpg.Connection,
    session_id: UUID
) -> Optional[asyncpg.Record]:
    """Retrieve a game session by ID."""
    return await conn.fetchrow("""
        SELECT id, edition, remaining
        FROM game_sessions
        WHERE id = $1 AND completed = FALSE
    """, session_id)


async def get_session_any(
    conn: asyncpg.Connection,
    session_id: UUID
) -> Optional[asyncpg.Record]:
    """Retrieve a game session by ID regardless of completion state."""
    return await conn.fetchrow("""
        SELECT id, edition, remaining, completed
        FROM game_sessions
        WHERE id = $1
    """, session_id)


async def update_session_decision(
    conn: asyncpg.Connection,
    session_id: UUID,
    item_id: int,
    decision: str  # 'keep' or 'cut'
) -> asyncpg.Record:
    """Record decision, increment appropriate counter, decrement remaining."""
    if decision == 'keep':
        return await conn.fetchrow("""
            UPDATE game_sessions
            SET
                shown_ids = array_append(shown_ids, $2),
                kept_count = kept_count + 1,
                remaining = remaining - 1,
                updated_at = NOW()
            WHERE id = $1
            RETURNING id, remaining, shown_ids, kept_count, cut_count
        """, session_id, item_id)
    else:  # cut
        return await conn.fetchrow("""
            UPDATE game_sessions
            SET
                shown_ids = array_append(shown_ids, $2),
                cut_count = cut_count + 1,
                remaining = remaining - 1,
                updated_at = NOW()
            WHERE id = $1
            RETURNING id, remaining, shown_ids, kept_count, cut_count
        """, session_id, item_id)
    

# ===== Open mode functions =====

async def create_open_session(
    conn: asyncpg.Connection,
    session_id: UUID,
    edition: str,
    item_ids: List[int]
) -> asyncpg.Record:
    """Create a session for open mode with predefined list of 8 items."""
    return await conn.fetchrow("""
        INSERT INTO game_sessions (id, edition, item_ids, remaining)
        VALUES ($1, $2, $3, 8)
        RETURNING id, edition, item_ids, remaining, created_at
    """, session_id, edition, item_ids)


async def get_open_session(
    conn: asyncpg.Connection,
    session_id: UUID
) -> Optional[asyncpg.Record]:
    """Retrieve an open session (including item_ids array)."""
    return await conn.fetchrow("""
        SELECT id, edition, item_ids, remaining, kept_count, cut_count, completed
        FROM game_sessions
        WHERE id = $1 AND completed = FALSE
    """, session_id)


async def update_open_session_decision(
    conn: asyncpg.Connection,
    session_id: UUID,
    item_id: int,
    decision: str
) -> asyncpg.Record:
    """Record a keep/cut decision, increment counter, decrement remaining.
       Returns the updated session (remaining, kept_count, cut_count)."""
    if decision == 'keep':
        return await conn.fetchrow("""
            UPDATE game_sessions
            SET kept_count = kept_count + 1,
                remaining = remaining - 1,
                updated_at = NOW()
            WHERE id = $1 AND $2 = ANY(item_ids)
            RETURNING remaining, kept_count, cut_count
        """, session_id, item_id)
    else:
        return await conn.fetchrow("""
            UPDATE game_sessions
            SET cut_count = cut_count + 1,
                remaining = remaining - 1,
                updated_at = NOW()
            WHERE id = $1 AND $2 = ANY(item_ids)
            RETURNING remaining, kept_count, cut_count
        """, session_id, item_id)


async def get_random_items(
    conn: asyncpg.Connection,
    edition: str,
    limit: int
) -> List[asyncpg.Record]:
    return await conn.fetch("""
        SELECT id, name, image_url, edition
        FROM items
        WHERE edition = $1
        ORDER BY RANDOM()
        LIMIT $2
    """, edition, limit)


async def get_random_unshown_items(
    conn: asyncpg.Connection,
    edition: str,
    shown_ids: List[int],
    count: int
) -> List[asyncpg.Record]:
    """
    Fetch `count` random distinct items from the given edition
    that are NOT in `shown_ids`.
    """
    if count <= 0:
        return []
    return await conn.fetch("""
        SELECT id, name, image_url, edition
        FROM items
        WHERE edition = $1
          AND id != ALL($2::int[])
        ORDER BY RANDOM()
        LIMIT $3
    """, edition, shown_ids, count)


async def mark_session_complete(
    conn: asyncpg.Connection,
    session_id: UUID
) -> str:
    """Mark a game session as completed."""
    await conn.execute("""UPDATE game_sessions 
                       SET completed = TRUE 
                       WHERE id = $1""", session_id)
    return "OK"


async def delete_stale_sessions(
    conn: asyncpg.Connection,
    hours: int = 1
) -> int:
    """Delete sessions not updated in the last `hours` hours. Returns number deleted."""
    result = await conn.execute("""
        DELETE FROM game_sessions
        WHERE updated_at < NOW() - ($1 || ' hours')::INTERVAL
    """, hours)
    # Extract number of rows deleted from command status (e.g., "DELETE 5")
    return int(result.split()[-1]) if result.startswith("DELETE") else 0


# =====================================================
# Votes (Analytics)
# =====================================================

async def insert_vote(
    conn: asyncpg.Connection,
    session_id: UUID,
    item_id: int,
    edition: str,
    decision: str
) -> None:
    """Record a single vote (keep or cut) for analytics."""
    await conn.execute("""
        INSERT INTO votes (session_id, item_id, edition, decision)
        VALUES ($1, $2, $3, $4)
    """, session_id, item_id, edition, decision)


async def get_session_items(
    conn: asyncpg.Connection,
    session_id: UUID
) -> tuple[List[int], List[int]]:
    """Return (kept_ids, cut_ids) for a session."""
    kept = await conn.fetch("""
        SELECT item_id FROM votes
        WHERE session_id = $1 AND decision = 'keep'
        ORDER BY voted_at
    """, session_id)
    cut = await conn.fetch("""
        SELECT item_id FROM votes
        WHERE session_id = $1 AND decision = 'cut'
        ORDER BY voted_at
    """, session_id)
    return [row["item_id"] for row in kept], [row["item_id"] for row in cut]


async def get_session_items_with_details(
    conn: asyncpg.Connection,
    session_id: UUID
) -> tuple[List[dict], List[dict]]:
    """
    Retrieve kept and cut items (full details) for a session.
    Returns (kept_items, cut_items) where each item is a dict with keys:
    id, name, image_url, edition.
    """
    # Fetch kept items
    kept_rows = await conn.fetch("""
        SELECT i.id, i.name, i.image_url, i.edition
        FROM votes v
        JOIN items i ON v.item_id = i.id
        WHERE v.session_id = $1 AND v.decision = 'keep'
        ORDER BY v.voted_at
    """, session_id)
    kept_items = [dict(row) for row in kept_rows]

    # Fetch cut items
    cut_rows = await conn.fetch("""
        SELECT i.id, i.name, i.image_url, i.edition
        FROM votes v
        JOIN items i ON v.item_id = i.id
        WHERE v.session_id = $1 AND v.decision = 'cut'
        ORDER BY v.voted_at
    """, session_id)
    cut_items = [dict(row) for row in cut_rows]

    return kept_items, cut_items

# =====================================================
# Leaderboards
# =====================================================

async def top_kept_items(
    conn: asyncpg.Connection,
    edition: str,
    limit: int = 10
) -> List[asyncpg.Record]:
    """Return the most kept items for a given edition."""
    return await conn.fetch("""
        SELECT 
            i.id,
            i.name,
            i.image_url,
            COUNT(v.id) as keep_count
        FROM votes v
        JOIN items i ON v.item_id = i.id
        WHERE v.edition = $1 AND v.decision = 'keep'
        GROUP BY i.id, i.name, i.image_url
        ORDER BY keep_count DESC
        LIMIT $2
    """, edition, limit)


async def top_cut_items(
    conn: asyncpg.Connection,
    edition: str,
    limit: int = 10
) -> List[asyncpg.Record]:
    """Return the most cut items for a given edition."""
    return await conn.fetch("""
        SELECT 
            i.id,
            i.name,
            i.image_url,
            COUNT(v.id) as cut_count
        FROM votes v
        JOIN items i ON v.item_id = i.id
        WHERE v.edition = $1 AND v.decision = 'cut'
        GROUP BY i.id, i.name, i.image_url
        ORDER BY cut_count DESC
        LIMIT $2
    """, edition, limit)
