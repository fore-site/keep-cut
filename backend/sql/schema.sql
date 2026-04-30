-- =====================================================
-- Database schema for Keep-Cut Game
-- PostgreSQL required (uses UUID, triggers)
-- Three editions: anime, movies, tv_shows
-- =====================================================

-- 1. Items table: stores all anime / movies / TV shows
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER UNIQUE,
    anilist_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    image_url TEXT,
    edition TEXT NOT NULL CHECK (edition IN ('anime', 'movies', 'tv_shows')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Game sessions: track active games (no arrays, only progress)
CREATE TABLE IF NOT EXISTS game_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    edition TEXT NOT NULL CHECK (edition IN ('anime', 'movies', 'tv_shows')),
    remaining INTEGER DEFAULT 8,           -- how many choices left (counts down from 8)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Votes table: records every keep/cut decision individually
CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id),
    edition TEXT NOT NULL CHECK (edition IN ('anime', 'movies', 'tv_shows')),
    decision TEXT NOT NULL CHECK (decision IN ('keep', 'cut')),
    voted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- Indexes for performance
-- =====================================================

-- Items: random selection per edition
CREATE INDEX IF NOT EXISTS idx_items_edition ON items(edition);

-- Game sessions: clean up old sessions
CREATE INDEX IF NOT EXISTS idx_game_sessions_updated ON game_sessions(updated_at);
CREATE INDEX IF NOT EXISTS idx_game_sessions_edition ON game_sessions(edition);

-- Votes: fast analytics queries
CREATE INDEX IF NOT EXISTS idx_votes_edition_decision ON votes(edition, decision);
CREATE INDEX IF NOT EXISTS idx_votes_item_id ON votes(item_id);
CREATE INDEX IF NOT EXISTS idx_votes_session_id ON votes(session_id);
CREATE INDEX IF NOT EXISTS idx_votes_voted_at ON votes(voted_at);

-- =====================================================
-- Auto-update updated_at on game_sessions
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_game_sessions_updated_at ON game_sessions;
CREATE TRIGGER trigger_update_game_sessions_updated_at
    BEFORE UPDATE ON game_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Optional: Verify counts
-- SELECT edition, COUNT(*) FROM items GROUP BY edition;
-- =====================================================