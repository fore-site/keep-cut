import asyncpg
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from app.config import DEBUG, APP_NAME, CORS_ORIGINS
from app.db import init_db_pool, close_db_pool, get_db
from app.routers import keep_cut, items, votes, keep_cut_open
from .limiter import limiter

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


# Configure logging
logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager for FastAPI – handles startup and shutdown events.
    """
    
    logger.info("Starting up...")
    await init_db_pool()
    logger.info("Database pool initialized.")
    yield
    
    logger.info("Shutting down...")
    await close_db_pool()
    logger.info("Database pool closed.")


app = FastAPI(
    title=APP_NAME,
    debug=DEBUG,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(keep_cut.router)
app.include_router(keep_cut_open.router)
app.include_router(items.router)
app.include_router(votes.router)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
async def root():
    return {"message": f"Welcome to {APP_NAME}"}


@app.get("/health", status_code=200)
async def health_check(conn: asyncpg.Connection = Depends(get_db)):
    """
    Standard health check that verifies database connectivity.
    Returns:
        - 200 OK with status "healthy" if DB is reachable
        - 503 Service Unavailable if DB is down
    """
    try:
        await conn.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )