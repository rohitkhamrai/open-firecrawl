import asyncio
from ddgs import DDGS
from engine.extractor import extract_schema
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown

def _get_search_urls(keyword: str, max_urls: int = 10) -> list[str]:
    """Uses DDGS to find top URLs for the keyword, bypassing basic blocks via primp."""
    print(f"Keyword Agent [Search]: Querying DDG for '{keyword}'...", flush=True)
    urls = []
    import time
    try:
        with DDGS() as ddgs:
            # Query 1: General info & temples
            results1 = list(ddgs.text(f"{keyword} famous temples locations India", max_results=5))
            time.sleep(3)
            # Query 2: Cost & booking
            results2 = list(ddgs.text(f"{keyword} pandit cost price rupees INR", max_results=30))
            time.sleep(3)
            # Query 3: Social & trending
            results3 = list(ddgs.text(f"{keyword} trending instagram facebook hashtag", max_results=3))
            
            for res in results1 + results2 + results3:
                if res.get('href') and res['href'] not in urls:
                    urls.append(res['href'])
                    
    except Exception as e:
        print(f"Keyword Agent [Search]: DDG search failed: {e}", flush=True)
        
    final_urls = urls[:max_urls]
    print(f"Keyword Agent [Search]: Found {len(final_urls)} unique URLs.", flush=True)
    return final_urls

async def _scrape_url(url: str, sem: asyncio.Semaphore) -> str:
    """Uses the Deep Crawler logic (Playwright StealthyFetcher) to scrape a URL."""
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
    """
    New Architecture:
    1. Search for top URLs (DDGS).
    2. Deep Scrape the URLs (StealthyFetcher).
    3. LLM Synthesis -> JSON.
    """
    print(f"Keyword Agent: Starting unified search+scrape pipeline on '{keyword}'", flush=True)
    
    # Step 1: Get URLs (increased from 15 to 30 to guarantee enough pricing links)
    urls = await asyncio.to_thread(_get_search_urls, keyword, 30)
    if not urls:
        print("Keyword Agent: No URLs found via search.", flush=True)
        # Fallback to wiki if search is completely blocked
        urls = [f"https://en.wikipedia.org/wiki/{keyword.replace(' ', '_')}"]
        
    # Step 2: Scrape URLs concurrently using the global config limit (default 10)
    sem = asyncio.Semaphore(10)  # Bumped from 2 to 10 for massive speedup
    tasks = [_scrape_url(url, sem) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_markdowns = [r for r in results if isinstance(r, str) and r.strip()]
    
    # Bypassing IG/FB Login Walls: Inject raw DDG search snippets directly into markdown
    # because DDG already indexed the likes/views in its text preview!
    social_snippets = ""
    try:
        with DDGS() as ddgs:
            # Query Reels and Posts explicitly for engagement metrics
            for res in ddgs.text(f"{keyword} site:instagram.com/p/ OR site:instagram.com/reel/ OR site:facebook.com/posts/", max_results=6):
                social_snippets += f"## Source: {res.get('href')}\n[SYSTEM META: Post Engagement Metrics]\nSearch Snippet: {res.get('title')} - {res.get('body')}\n[END SYSTEM META]\n\n"
    except Exception:
        pass
        
    combined_markdown = social_snippets + "\n".join(valid_markdowns)
    
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
                        "price": {"type": "string", "description": "The price or cost range mentioned (e.g. 'Rs 500' or '1000 - 5000 INR')."}
                    },
                    "required": ["source", "price"]
                },
                "description": "A list of cost estimates found across different websites to compare prices."
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
