import asyncio
import os
import pytest
import pytest_asyncio
import asyncpg
import httpx
from asgi_lifespan import LifespanManager

# Set environment variable for testing
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:Bobo7711.@localhost:5432/keep_cut")
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_test_database():
    """Create and tear down the test database schema."""
    # Connect to the test database
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    
    # Drop and recreate tables (clean slate)
    await conn.execute("""
        DROP TABLE IF EXISTS votes CASCADE;
        DROP TABLE IF EXISTS game_sessions CASCADE;
        DROP TABLE IF EXISTS items CASCADE;
    """)
    
    # Run schema.sql
    with open("../backend/sql/schema.sql", "r") as f:
        schema_sql = f.read()
    await conn.execute(schema_sql)
    
    # Insert sample items for testing
    await conn.execute("""
        INSERT INTO items (name, image_url, edition) VALUES
        ('Anime1', 'http://example.com/anime1.jpg', 'anime'),
        ('Anime2', 'http://example.com/anime2.jpg', 'anime'),
        ('Anime3', 'http://example.com/anime3.jpg', 'anime'),
        ('Anime4', 'http://example.com/anime4.jpg', 'anime'),
        ('Anime5', 'http://example.com/anime5.jpg', 'anime'),
        ('Anime6', 'http://example.com/anime6.jpg', 'anime'),
        ('Anime7', 'http://example.com/anime7.jpg', 'anime'),
        ('Anime8', 'http://example.com/anime8.jpg', 'anime'),
        ('Movie1', 'http://example.com/movie1.jpg', 'movies'),
        ('Movie2', 'http://example.com/movie2.jpg', 'movies'),
        ('TV1', 'http://example.com/tv1.jpg', 'tv_shows'),
        ('TV2', 'http://example.com/tv2.jpg', 'tv_shows')
    """)
    
    yield
    
    # Cleanup after tests
    await conn.execute("DROP TABLE votes, game_sessions, items CASCADE")
    await conn.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_sessions(setup_test_database):
    """Clear game_sessions and votes before each test."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("DELETE FROM game_sessions")
    await conn.execute("DELETE FROM votes")
    await conn.close()


@pytest_asyncio.fixture
async def db_connection():
    """Provide a direct database connection for tests that need it."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def client():
    """Async test client using ASGI transport."""
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
