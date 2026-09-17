import json
import asyncpg
from config import settings

pool = None

async def init_db():
    """Initializes the database table for storing scraped data."""
    global pool
    if not settings.NEON_DATABASE_URL:
        print("Warning: NEON_DATABASE_URL is empty. Database storage is disabled.")
        return
        
    try:
        pool = await asyncpg.create_pool(settings.NEON_DATABASE_URL)
        async with pool.acquire() as conn:
            # ponytail: create table directly, keep vector nullable for future use.
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS scrapes (
                    url TEXT PRIMARY KEY,
                    schema_data JSONB,
                    embedding VECTOR(1536)
                );
            """)
            print("Database initialized.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        pool = None

async def close_db():
    global pool
    if pool:
        await pool.close()

async def save_scrape(url: str, data: dict):
    """Saves the scraped JSON payload to the database."""
    global pool
    if not pool:
        print(f"Skipping DB save for {url} (pool not initialized).")
        return
        
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO scrapes (url, schema_data)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (url) DO UPDATE 
                SET schema_data = EXCLUDED.schema_data;
            """, url, json.dumps(data))
            print(f"Saved {url} to database.")
    except Exception as e:
        print(f"Failed to save data for {url}: {e}")
