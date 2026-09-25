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

## 4. Free/Cheap Upgrade Options (Future Scaling)
If you need to scale this from 100 poojas a week to 10,000 poojas a week without paying massive enterprise fees, implement these upgrades:

1. **Self-Hosted SearxNG (Free)**: DuckDuckGo will eventually ban your server IP if volume increases. Deploy a SearxNG Docker container on your Ubuntu server. It routes queries through Google, Bing, and DDG simultaneously, acting as a free proxy rotator.
2. **OpenAI / Anthropic Batch API (Cheap)**: Free OpenRouter models are unstable and occasionally hallucinate. Switch to OpenAI's **Batch API** (using `gpt-4o-mini`). It provides a 50% discount and zero rate limits because you upload a `.jsonl` file and they process it offline over 24 hours. It would cost mere pennies to process thousands of poojas perfectly.
3. **Local Ollama Extraction (Free)**: Since you are running an Ubuntu server, if you have a mid-range GPU (or high-end CPU), install **Ollama**. Run `llama3.1:8b` locally. Point `engine/extractor.py` to `localhost:11434`. You get infinite, uncensored, free extractions with zero network latency or rate limits.
