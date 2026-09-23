import asyncio
import json
import engine.db as db

async def main():
    print("Testing Postgres insertion...")
    await db.init_db()
    with open("output.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    await db.save_keyword("Satyanarayan Pooja", data)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
