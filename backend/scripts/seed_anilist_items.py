#!/usr/bin/env python3
"""
Seed top 500 anime from AniList API.
AniList rate limit: 90 requests per minute.
We'll fetch 50 items per page, so 10 pages total (500 items).
Built-in delay (0.7s) keeps us well under the limit.
"""

import os
import sys
import json
import time
import asyncio
import asyncpg
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from app.config import DATABASE_URL

# Add parent directory to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

ANILIST_API_URL = "https://graphql.anilist.co"

# Configuration
ITEMS_PER_PAGE = 50      # API max is 50
TOTAL_ITEMS = 500        # Will fetch 10 pages (50 * 10)
PAGE_DELAY_SECONDS = 0.7 # Stay under 90 req/min (max 1.5s per page)

# Headers (User-Agent required by AniList)
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "KeepCut-Game/1.0 (https://github.com/fore-site/keep-cut)"
}


def build_graphql_query(per_page: int, page: int) -> dict:
    """
    Build GraphQL query for paginated anime list.
    Sorted by popularity (most to least) to get top anime.
    """
    query = """
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            pageInfo {
                hasNextPage
                total
            }
            media(type: ANIME, sort: POPULARITY_DESC) {
                id
                title {
                    romaji
                    english
                    native
                }
                coverImage {
                    large
                    extraLarge
                }
            }
        }
    }
    """
    variables = {"page": page, "perPage": per_page}
    return {"query": query, "variables": variables}


def extract_best_title(media: dict) -> str:
    """
    Extract best available title: English > Romaji > Native.
    """
    title_data = media.get("title", {})
    return title_data.get("english") or title_data.get("romaji") or title_data.get("native", "Unknown")


def extract_cover_url(media: dict) -> Optional[str]:
    """
    Extract cover image URL. Prefer extraLarge, fallback to large.
    """
    cover = media.get("coverImage", {})
    return cover.get("extraLarge") or cover.get("large")


def fetch_page(page: int, per_page: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a single page of anime from AniList API.
    Returns dict with list of anime and hasNextPage flag.
    """
    payload = build_graphql_query(per_page, page)

    try:
        response = requests.post(ANILIST_API_URL, json=payload, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            print(f"GraphQL errors on page {page}: {data['errors']}")
            return None

        page_data = data.get("data", {}).get("Page", {})
        media_list = page_data.get("media", [])
        page_info = page_data.get("pageInfo", {})

        return {
            "anime_list": media_list,
            "has_next_page": page_info.get("hasNextPage", False)
        }

    except requests.exceptions.RequestException as e:
        print(f"Request failed on page {page}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error on page {page}: {e}")
        return None


def chunk_list(data_list: List[Dict], chunk_size: int = 100):
    """
    Yield successive chunks from a list for batch insertion.
    """
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i:i + chunk_size]


async def insert_anime_batch(pool: asyncpg.Pool, batch: List[Dict]) -> int:
    """
    Insert a batch of anime into the database.
    Returns number of rows inserted.
    """
    inserted_count = 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            for anime in batch:
                anilist_id = anime.get("id")
                title = anime.get("title")
                image_url = anime.get("image_url")

                if not anilist_id or not title:
                    continue

                try:
                    await conn.execute("""
                        INSERT INTO items (anilist_id, name, image_url, edition)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (anilist_id) DO NOTHING
                    """, anilist_id, title, image_url, "anime")
                    inserted_count += 1
                except Exception as e:
                    print(f"Failed to insert anime ID {anilist_id}: {e}")

    return inserted_count


async def main():
    """
    Main orchestration function.
    """
    print("Starting AniList seeding script...")
    print(f"Target: {TOTAL_ITEMS} anime ({ITEMS_PER_PAGE} per page)")

    # Collect anime data from all pages
    all_anime = []
    current_page = 1
    consecutive_failures = 0
    max_consecutive_failures = 3

    while len(all_anime) < TOTAL_ITEMS:
        print(f"Fetching page {current_page}...", end=" ", flush=True)

        result = fetch_page(current_page, ITEMS_PER_PAGE)

        if result is None:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                print(f"\nToo many consecutive failures ({max_consecutive_failures}). Stopping.")
                break
            print(f"Failed (attempt {consecutive_failures}/{max_consecutive_failures}). Retrying after delay...")
            time.sleep(PAGE_DELAY_SECONDS * 2)
            continue

        consecutive_failures = 0
        anime_list = result["anime_list"]

        if not anime_list:
            print("No more anime found. Stopping.")
            break

        # Transform and append
        for media in anime_list:
            title = extract_best_title(media)
            cover_url = extract_cover_url(media)

            all_anime.append({
                "id": media.get("id"),
                "title": title,
                "image_url": cover_url,
            })

        print(f"Got {len(anime_list)} anime (Total: {len(all_anime)})")

        # Stop if no more pages
        if not result.get("has_next_page", False):
            print("Reached last page.")
            break

        current_page += 1
        time.sleep(PAGE_DELAY_SECONDS)

    print(f"\nCollected {len(all_anime)} anime total.")

    if not all_anime:
        print("No anime data collected. Exiting.")
        return

    # Connect to database and insert
    print("Connecting to database...")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

    try:
        total_inserted = 0
        batches = chunk_list(all_anime, chunk_size=100)

        for i, batch in enumerate(batches, 1):
            print(f"Inserting batch {i} ({len(batch)} items)...")
            inserted = await insert_anime_batch(pool, batch)
            total_inserted += inserted
            print(f"   Inserted {inserted} new rows")

    finally:
        await pool.close()

    print(f"\nSeeding complete. Inserted {total_inserted} out of {len(all_anime)} anime.")


if __name__ == "__main__":
    asyncio.run(main())