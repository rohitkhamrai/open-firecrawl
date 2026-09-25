import asyncio
import time
import sys
import engine.db as db
from engine.keyword import run_keyword_agent

async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_batch.py poojas.txt")
        return
        
    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            poojas = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Failed to read file {filename}: {e}")
        return
        
    print(f"Loaded {len(poojas)} poojas for batch processing.")
    
    await db.init_db()
    
    for i, pooja in enumerate(poojas):
        print(f"\n[{i+1}/{len(poojas)}] Starting scrape for: {pooja}")
        
        try:
            result = await run_keyword_agent(pooja)
            
            # Validation Step
            has_pricing = len(result.get("cost_estimates", [])) > 0
            has_info = bool(result.get("pooja_info", {}).get("what"))
            has_social = len(result.get("social_media_traction", {}).get("top_posts", [])) > 0
            
            if not has_info and not has_pricing and not has_social:
                print(f"[!] Validation failed for {pooja}: Insufficient data extracted.")
            else:
                await db.save_keyword(pooja, result)
                print(f"[*] Successfully saved {pooja} to database.")
                
        except Exception as e:
            print(f"[!] Error processing {pooja}: {e}")
            
        if i < len(poojas) - 1:
            print(f"Sleeping for 90 seconds to avoid DDG and LLM rate limits...")
            time.sleep(90) # 90 seconds perfectly avoids DDG and Groq rate limits
            
    await db.close_db()
    print("\nBatch processing complete.")

if __name__ == "__main__":
    asyncio.run(main())
