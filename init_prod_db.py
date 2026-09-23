import asyncio
import engine.db as db

async def main():
    print("Initializing prod_scrap database tables...")
    await db.init_db()
    print("Empty tables successfully created in prod_scrap!")

if __name__ == "__main__":
    asyncio.run(main())
