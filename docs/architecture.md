# Daiv Bharati Scraper Architecture & Flow

This document explains the architecture, the tools used, the workflow, and future production upgrade paths for the Daiv Bharati Pooja Scraper.

## 1. What's Used & Why
- **FastAPI / Python**: The backend framework. Lightweight, handles async tasks perfectly for fetching websites in parallel.
- **DuckDuckGo Search (DDGS)**: Used to dynamically discover Wikipedia pages, pricing/booking websites, and Instagram/Facebook reels for a specific pooja. It is completely free and requires no API keys.
- **Playwright / httpx (Deep Scrape)**: Downloads the raw HTML of the websites discovered in the search phase.
- **Markdown Conversion (BeautifulSoup / html2text)**: Converts bloated HTML into clean markdown. This reduces the text size by 90%, allowing it to fit into free LLM token limits while retaining all the actual text data.
- **AsyncGroq / OpenRouter API**: Used for AI extraction. It reads the raw markdown and intelligently populates the strict JSON schema (pricing, history, social media metrics). We use multiple free keys and round-robin them.
- **PostgreSQL (Neon)**: A cloud database used to store the structured JSON data. Neon has an excellent free tier and integrates natively with Python `asyncpg`.

## 2. The Flow of Work
The process starts when `run_batch.py` is executed (designed to run once a week).

1. **Batch Processing**: Reads `poojas.txt` line by line.
2. **Search Discovery (`engine/keyword.py`)**:
   - Queries DDG for History/Rituals (Top 2 sites marked for deep scrape).
   - Queries DDG for Booking/Pricing (Top 8 sites marked for deep scrape to guarantee 7+ pricing options).
   - Queries DDG for Instagram Reels / FB Watch videos (Top 5 video links grabbed as lightweight text snippets).
3. **Deep Scraping (`engine/fetcher.py`)**: Connects to the Top 10 sites identified above and downloads their full text.
4. **LLM Synthesis (`engine/extractor.py`)**: 
   - The aggregated text is chunked into 12,000-character blocks.
   - The script pulls a healthy API key from the `ResourcePool`.
   - The AI processes each chunk and outputs a strict JSON payload containing the Pooja details, pricing packages, and social media likes/views.
   - If an API key hits a rate limit (429 Error), the system automatically puts that key on a 35-second cooldown and uses the next available key.
5. **Validation & Storage (`main.py` / `engine/db.py`)**:
   - Validates that the AI actually extracted pricing, info, and social data.
   - Saves the final, validated JSON object to the PostgreSQL database.
   - Sleeps for 90 seconds to avoid DDG/LLM IP bans, then proceeds to the next pooja.

## 3. Security & Production Readiness
- **Vulnerability Status (Pass)**: The database integration (`engine/db.py`) uses parameterized SQL queries (`$1`, `$2::jsonb`). This makes SQL Injection structurally impossible. API keys are handled securely via environment variables (`.env`).
- **Production Status (Pass)**: The previous FastAPI architecture was highly unstable for automation due to HTTP timeouts and instant rate-limit cascading. The current `run_batch.py` architecture is 100% production-ready for a weekly cron job. The 90-second sleep and 35-second API Key cooldown completely resolves rate limit failures.


## 5. Database Approach (PostgreSQL)
The scraper uses a robust, schema-less JSONB approach to store data in PostgreSQL. This gives us the rigid structure of a relational database with the dynamic flexibility of a NoSQL document store.

### The Tables
We maintain a primary table named `keyword_data` designed specifically for the batch pooja scraper:
- `keyword (TEXT PRIMARY KEY)`: The name of the pooja (e.g., 'Ashlesha Bali Pooja'). Using this as a primary key guarantees no duplicate entries are ever created, even if the scraper runs twice on the same file.
- `schema_data (JSONB)`: The entire validated JSON payload extracted by the LLM (containing pooja details, pricing arrays, and social media URLs). We use `JSONB` because it stores the JSON in a decomposed binary format, allowing incredibly fast indexing and querying of nested keys directly via SQL.
- `created_at (TIMESTAMP)`: Automatically tracks when the scrape occurred.

### How & When Data is Saved
1. **Validation First**: Data is NOT blindly written to the database. Before inserting, `main.py` asserts that the LLM successfully extracted at least one pricing point, one social post, or basic information. If it's a hallucination or an empty scrape, the database write is blocked.
2. **Upsert Logic (`ON CONFLICT DO UPDATE`)**: When `db.save_keyword()` is called, it executes an "Upsert" query. If the pooja doesn't exist, a new row is created. If the pooja *already exists* (meaning you are re-running a weekly scrape to get updated prices or likes), it automatically overwrites the old `schema_data` with the fresh scrape.
3. **Connection Pooling**: We use `asyncpg` to maintain an active connection pool to the Ubuntu Postgres server. This is vastly superior to opening/closing a connection on every single insert, preventing connection-exhaustion crashes during heavy batch workloads.

## 6. LLM Extraction (Groq & Schema)
The synthesis phase relies on **Groq** and **OpenRouter** API keys. Due to their strict rate limits on free tiers, we use an automated `ResourcePool` to cycle through multiple API keys and apply a 35-second cooldown whenever a `429 Too Many Requests` error is encountered. 

The LLM is prompted to strictly extract data into a specific JSON schema, which guarantees consistency for the frontend. The `schema_data` JSONB field stored in the database contains:

- `pooja_info` (Object):
  - `what`: A clear explanation of what the pooja is.
  - `why`: The mythological significance and purpose.
  - `how`: A step-by-step concrete procedure for performing it.
- `where` (Array of Strings): Famous temple names and locations across India where this specific pooja is celebrated.
- `who_is_doing_it` (Array of Strings): Information on demographics, priests, and notable devotees participating.
- `cost_estimates` (Array of Objects): 
  - Each object contains a `source` (website URL) and a `price` (strictly enforced to be a total currency cost like "Rs. 2500", aggressively rejecting promotional text like "101 advance fee").
- `social_media_traction` (Object):
  - `top_posts`: Array of objects containing `post_url` (strictly limited to `instagram.com` or `facebook.com` video links), `likes`, and `views`.
  - `hashtags`: Array of popular trending hashtags related to the pooja.
