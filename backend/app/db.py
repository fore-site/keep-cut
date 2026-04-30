import asyncpg
from asyncpg.pool import Pool
from typing import Optional
import logging

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Global variable to hold the connection pool
_pool: Optional[Pool] = None


async def init_db_pool() -> Pool:
    """
    Initialize and return the asyncpg connection pool.
    Call this once during application startup.
    """
    global _pool
    if _pool is not None:
        logger.warning("Database pool already initialized")
        return _pool

    logger.info("Creating database pool...")
    try:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,          
            max_size=10,         
            command_timeout=60,  
            max_queries=50000,   
            max_inactive_connection_lifetime=300, 
        )
        logger.info("Database pool created successfully")
        return _pool
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise


async def close_db_pool() -> None:
    """Close the connection pool gracefully on shutdown."""
    global _pool
    if _pool is None:
        logger.warning("No database pool to close")
        return
    logger.info("Closing database pool...")
    await _pool.close()
    _pool = None
    logger.info("Database pool closed")


async def get_db() -> asyncpg.Connection:
    """
    Dependency function to get a connection from the pool.
    Use it in route handlers with `Depends(get_db)`.
    
    Example:
        @router.get("/test")
        async def test(conn: asyncpg.Connection = Depends(get_db)):
            result = await conn.fetch("SELECT 1")
            return result
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    async with _pool.acquire() as conn:
        yield conn
