import asyncio
import asyncpg
import sys

async def main():
    db_url = "postgresql://postgres:postgres@192.168.0.134:15432/postgres"
    print("Connecting to default postgres database...")
    try:
        conn = await asyncpg.connect(db_url)
        # CREATE DATABASE cannot run inside a transaction block, so we use execute
        await conn.execute("CREATE DATABASE prod_scrap")
        print("Successfully created database 'prod_scrap'!")
        await conn.close()
    except asyncpg.exceptions.DuplicateDatabaseError:
        print("Database 'prod_scrap' already exists!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
