import asyncio
from ddgs import DDGS
from engine.extractor import extract_schema
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown

def _get_search_urls_and_snippets(keyword: str):
    """Uses DDGS to find top URLs. Separates deep-scrape targets from snippet-only targets."""
    print(f"Keyword Agent [Search]: Querying DDG for '{keyword}'...", flush=True)
    deep_urls = []
    snippets = []
    
    import time
    
    # Query 1: General info -> DEEP SCRAPE (Top 2)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{keyword} pooja history benefits rituals significance", max_results=3))
            for res in results[:2]:
                if res.get('href'):
                    deep_urls.append(res['href'])
    except Exception as e:
        print(f"Keyword Agent [Search Q1]: DDG search failed: {e}", flush=True)
        
    time.sleep(2)
    
    # Query 2: Cost & booking -> DEEP SCRAPE (Top 8) to guarantee 7+ pricings
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{keyword} book pandit online price packages", max_results=10))
            if results:
                # Deep scrape up to 8 booking sites to guarantee we extract enough pricings
                for res in results[:8]:
                    if res.get('href'):
                        deep_urls.append(res['href'])
    except Exception as e:
        print(f"Keyword Agent [Search Q2]: DDG search failed: {e}", flush=True)
        
    time.sleep(2)
    
    # Query 3: Social & trending (Videos only) -> SNIPPETS (Top 5 links)
    snippets.append("## SOCIAL MEDIA POSTS (Use these for social_media_traction top_posts)")
    try:
        with DDGS() as ddgs:
            for res in ddgs.text(f"{keyword} site:instagram.com/reel/ OR site:facebook.com/watch", max_results=5):
                if res.get('href'):
                    snippets.append(f"Source: {res['href']}\nTitle: {res.get('title')}\nInfo: {res.get('body')}\n")
    except Exception as e:
        print(f"Keyword Agent [Search Q3]: DDG search failed: {e}", flush=True)
        
    return deep_urls, "\n".join(snippets)

async def _scrape_url(url: str, sem: asyncio.Semaphore) -> str:
    """Uses the Deep Crawler logic to scrape a URL."""
    async with sem:
        print(f"Keyword Agent [Scrape]: Fetching {url}", flush=True)
        try:
            html, meta = await fetch_page(url)
            if meta.get("status_code", 500) == 200 and html:
                markdown = clean_html_to_markdown(html)
                print(f"Keyword Agent [Scrape]: {url} -> {len(markdown)} chars", flush=True)
                return f"## Source: {url}\n{markdown}\n\n"
        except Exception as e:
            print(f"Keyword Agent [Scrape]: Failed {url}: {e}", flush=True)
        return ""

async def run_keyword_agent(keyword: str) -> dict:
    print(f"Keyword Agent: Starting optimized pipeline on '{keyword}'", flush=True)
    
    # Step 1: Get Deep Scrape URLs and Lightweight Snippets
    deep_urls, snippet_text = await asyncio.to_thread(_get_search_urls_and_snippets, keyword)
    if not deep_urls:
        deep_urls = [f"https://en.wikipedia.org/wiki/{keyword.replace(' ', '_')}"]
        
    # Step 2: Scrape ONLY the top 2 general sites for deep details (what, why, how)
    sem = asyncio.Semaphore(5)
    tasks = [_scrape_url(url, sem) for url in deep_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_markdowns = [r for r in results if isinstance(r, str) and r.strip()]
    
    # Step 3: Combine Deep Markdown + Lightweight Snippets
    combined_markdown = "\n".join(valid_markdowns) + "\n\n" + snippet_text
    
    print(f"Keyword Agent: Aggregated {len(combined_markdown)} chars of markdown from {len(valid_markdowns)} sites.", flush=True)
    
    schema = {
        "type": "object",
        "properties": {
            "pooja_info": {
                "type": "object",
                "properties": {
                    "what": {"type": "string", "description": "What is this pooja? Clear explanation."},
                    "why": {"type": "string", "description": "Why is it performed? Significance, mythology, purpose."},
                    "how": {"type": "string", "description": "How is it performed? Concrete step-by-step process."}
                }
            },
            "where": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific famous temple names and locations in India where this pooja is celebrated. Extract real names from the text."
            },
            "who_is_doing_it": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Who performs or participates — devotees, demographics, priests, notable participants."
            },
            "cost_estimates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "The name or URL of the website where this price was found."},
                        "price": {"type": "string", "description": f"The price or cost range specifically for '{keyword}'. (e.g. 'Rs 500' or '1000 - 5000 INR')."}
                    },
                    "required": ["source", "price"]
                },
                "description": f"A list of cost estimates exclusively for '{keyword}'. CRITICAL: DO NOT extract prices for any other pooja or service."
            },
            "social_media_traction": {
                "type": "object",
                "properties": {
                    "top_posts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "post_url": {"type": "string", "description": "The exact URL of the social media post mentioned in the source."},
                                "likes": {"type": "string", "description": "Number of likes on the post extracted from the source or snippet. NEVER output 'Unknown' if a number is present in the text."},
                                "views": {"type": "string", "description": "Number of views on the post extracted from the source or snippet. NEVER output 'Unknown' if a number is present in the text."}
                            }
                        },
                        "description": "List of top social media posts with their links, likes, and views."
                    },
                    "hashtags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Popular hashtags for this topic on social media"
                    }
                }
            }
        }
    }
    
    print("Keyword Agent [Synthesis]: Running LLM extraction...", flush=True)
    result = await extract_schema(combined_markdown, schema)
    return result or {}
