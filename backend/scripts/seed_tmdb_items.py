import os
import sys
import asyncio
import asyncpg
import aiohttp
from dotenv import load_dotenv
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add parent directory to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")  # Your TMDB API key
DATABASE_URL = os.getenv("DATABASE_URL")  # Your PostgreSQL connection string

GENRE_MOVIE_SUPERHERO = 28  # Action genre ID, commonly used for superhero/comic movies

async def fetch_tmdb_config(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Fetch TMDB API configuration."""
    url = "https://api.themoviedb.org/3/configuration"
    params = {"api_key": TMDB_API_KEY}
    async with session.get(url, params=params) as resp:
        return await resp.json()

async def fetch_genre_mapping(session: aiohttp.ClientSession, media_type: str) -> Dict[int, str]:
    """Fetch genre ID to name mapping for movies or TV shows."""
    url = f"https://api.themoviedb.org/3/genre/{media_type}/list"
    params = {"api_key": TMDB_API_KEY}
    async with session.get(url, params=params) as resp:
        data = await resp.json()
        return {genre["id"]: genre["name"] for genre in data.get("genres", [])}

def build_item_payload(item: Dict, media_type: str, config: Dict) -> Dict:
    """Transform TMDB API response into a row for the items table."""
    tmdb_id = item.get("id")
    name = item.get("name") if media_type == "tv" else item.get("title")
    file_path = item.get("poster_path")
    image_url = None
    if file_path and config.get("images"):
        base_url = config["images"].get("secure_base_url")
        poster_size = "w342"  # Good balance between quality and file size, adjust as needed
        image_url = f"{base_url}{poster_size}{file_path}"
    return {
        "tmdb_id": tmdb_id,
        "name": name,
        "image_url": image_url,
        "edition": "tv_shows" if media_type == "tv" else "movies",
    }

async def fetch_and_store_items(
    pool: asyncpg.Pool,
    session: aiohttp.ClientSession,
    media_type: str,
    edition: str,
    config: Dict,
    total_needed: int = 500,
):
    """Generic function to fetch items from TMDB with pagination and store them."""
    fetched = 0
    page = 1
    items_to_insert: List[Dict] = []
    total_fetched_items = 0

    # Fetch existing tmdb_ids to avoid duplicates
    existing_ids = set()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT tmdb_id FROM items WHERE edition = $1", edition)
        existing_ids = {row["tmdb_id"] for row in rows if row["tmdb_id"]}
    logger.info(f"Found {len(existing_ids)} existing items for {edition}")

    while fetched < total_needed:
        url = f"https://api.themoviedb.org/3/discover/{media_type}"
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "page": page,
            "vote_count.gte": 100,
            "vote_average.gte": 5.0,
        }
        if media_type == "movie":
            params["with_genres"] = str(GENRE_MOVIE_SUPERHERO)

        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch {media_type} page {page}: {resp.status}")
                break
            data = await resp.json()
            results = data.get("results", [])
            total_fetched_items += len(results)

            if not results:
                logger.warning(f"No more results for {media_type} at page {page}. Breaking.")
                break

            for item in results:
                if fetched >= total_needed:
                    break
                tmdb_id = item.get("id")
                if tmdb_id in existing_ids:
                    continue
                payload = build_item_payload(item, media_type, config)
                if payload["name"]:
                    items_to_insert.append(payload)
                    fetched += 1
                    existing_ids.add(tmdb_id)

            if len(results) < 20:
                logger.warning(f"Page {page} for {media_type} has less than 20 items. Stopping.")
                break

            page += 1
            await asyncio.sleep(0.2)  # Slight delay to respect rate limits

    if items_to_insert:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for item in items_to_insert:
                    await conn.execute(
                        """
                        INSERT INTO items (tmdb_id, name, image_url, edition)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (tmdb_id) DO NOTHING
                        """,
                        item["tmdb_id"], item["name"], item["image_url"], item["edition"],
                    )
        logger.info(f"Inserted {len(items_to_insert)} new {edition} items")
    else:
        logger.info(f"No new items to insert for {edition}")

    logger.info(f"Total {edition} items fetched: {total_fetched_items}, new items inserted: {len(items_to_insert)}")
    logger.info(f"Completed fetching {media_type} data. Reached {fetched} items total (across all pages).")

async def main():
    """Main orchestration function."""
    logger.info("Starting TMDB seeding script...")

    async with aiohttp.ClientSession() as session:
        config = await fetch_tmdb_config(session)
        logger.info("Fetched TMDB configuration")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    try:
        async with aiohttp.ClientSession() as session:
            await fetch_and_store_items(pool, session, "tv", "tv_shows", config, total_needed=500)
            logger.info("Finished TV shows seeding.")
            await fetch_and_store_items(pool, session, "movie", "movies", config, total_needed=500)
            logger.info("Finished movies seeding.")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())