import asyncio
import json
from engine.keyword import run_keyword_agent

async def main():
    print("Testing Keyword Agent with updated max_results and prompt fixes...")
    result = await run_keyword_agent("Satyanarayan Pooja")
    
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    import engine.db as db
    await db.init_db()
    await db.save_keyword("Satyanarayan Pooja", result)
    
    print("\n================ EXTRACTION RESULT ================")
    print(json.dumps(result, indent=2))
    print("===================================================\n")
    print("Data saved to output.json and PostgreSQL database!")

if __name__ == "__main__":
    asyncio.run(main())
