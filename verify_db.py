import asyncio
import engine.db as db

async def main():
    pool = await __import__('asyncpg').create_pool("postgresql://postgres:postgres@192.168.0.134:5432/prod_scrap")
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT keyword, created_at FROM keyword_data")
        if not records:
            print("No records found in keyword_data table.")
        for row in records:
            print(f"Keyword: {row['keyword']}, Created: {row['created_at']}")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
