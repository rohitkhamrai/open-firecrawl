import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown
from engine.extractor import extract_schema, merge_json_outputs
from engine.router import rank_urls

def get_internal_links(html: str, base_url: str) -> list[str]:
    """Finds all internal URLs from the raw HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    base_domain = urlparse(base_url).netloc
    links = set()
    
    ignore_keywords = ['lang=', 'javascript:', 'mailto:', '#']
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if any(href.startswith(kw) for kw in ignore_keywords):
            continue
            
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        
        # Only same domain
        if parsed_url.netloc != base_domain:
            continue
            
        # Ignore assets
        if any(full_url.lower().endswith(ext) for ext in ['.jpg', '.png', '.pdf', '.css', '.js', '.svg', '.jpeg']):
            continue
            
        # Don't spider the root URL again
        if full_url.rstrip('/') == base_url.rstrip('/'):
            continue
            
        links.add(full_url)
        
    return list(links)

async def process_page(url: str, schema: dict, sem: asyncio.Semaphore) -> dict:
    """Processes a single page through the extraction pipeline."""
    async with sem:
        print(f"Spidering deep link: {url}", flush=True)
        html, metadata = await fetch_page(url)
        markdown = clean_html_to_markdown(html)
        return await extract_schema(markdown, schema)

async def crawl_domain(start_url: str, schema: dict, limit: int = 5) -> dict:
    """Crawls the root URL and deep pages via Stage 1 LLM Router."""
    print(f"Scraping root url: {start_url}", flush=True)
    html, metadata = await fetch_page(start_url)
    markdown = clean_html_to_markdown(html)
    
    # Extract root
    root_result = await extract_schema(markdown, schema)
    final_output = root_result if root_result else {}
    
    # Stage 1: Get all internal links and rank them via LLM
    all_links = get_internal_links(html, start_url)
    print(f"Found {len(all_links)} raw internal links. Routing through LLM Stage 1...", flush=True)
    
    nested_links = await rank_urls(all_links, limit)
    
    # Stage 2: Parallel Deep Scraping on Curated Links
    if nested_links:
        print(f"Stage 1 returned {len(nested_links)} high-value links. Beginning Stage 2 sequential scrape...", flush=True)
        sem = asyncio.Semaphore(1) # Max 1 concurrent headless browser to avoid OpenRouter free-tier rate limits
        tasks = [process_page(link, schema, sem) for link in nested_links]
        nested_results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_nested = [r for r in nested_results if r and not isinstance(r, Exception)]
        if valid_nested:
            final_output["extracted_pages"] = valid_nested
        for res in nested_results:
            if isinstance(res, Exception):
                print(f"Spider task failed: {res}", flush=True)
                
    return final_output
