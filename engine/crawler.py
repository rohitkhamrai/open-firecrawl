import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown
from engine.extractor import extract_schema, merge_json_outputs

def get_internal_links(html: str, base_url: str, max_links: int = 5) -> list[str]:
    """Finds up to max_links internal URLs from the raw HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    base_domain = urlparse(base_url).netloc
    links = set()
    
    ignore_keywords = ['about', 'contact', 'login', 'register', 'signin', 'signup', 'terms', 'privacy', 'faq', 'policy', 'cart', 'checkout', 'profile', 'lang=']
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
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
            
        path_and_query = (parsed_url.path + parsed_url.query).lower()
        if any(kw in path_and_query for kw in ignore_keywords):
            continue
            
        links.add(full_url)
        
    # Ponytail heuristic: prioritize URLs containing 'puja', 'epuja', 'product', 'book'
    # Fallback to sorting by path length (deep links usually have more path segments).
    def rank_url(u: str) -> int:
        score = len(urlparse(u).path)
        if 'puja' in u.lower() or 'epuja' in u.lower() or 'temple' in u.lower():
            score += 1000
        return score
        
    sorted_links = sorted(list(links), key=rank_url, reverse=True)
    return sorted_links[:max_links]

async def process_page(url: str, schema: dict, sem: asyncio.Semaphore) -> dict:
    """Processes a single page through the extraction pipeline."""
    async with sem:
        print(f"Spidering deep link: {url}", flush=True)
        html, metadata = await fetch_page(url)
        markdown = clean_html_to_markdown(html)
        return await extract_schema(markdown, schema)

async def crawl_domain(start_url: str, schema: dict) -> dict:
    """Crawls the root URL and up to 5 nested links, merging their schemas."""
    # ponytail: one pass spidering. Fetch root, extract links, fetch nested pages.
    print(f"Scraping root url: {start_url}", flush=True)
    html, metadata = await fetch_page(start_url)
    markdown = clean_html_to_markdown(html)
    
    # Extract root
    root_result = await extract_schema(markdown, schema)
    results = [root_result] if root_result else []
    
    # Spider nested links
    nested_links = get_internal_links(html, start_url, max_links=5)
    if nested_links:
        print(f"Found {len(nested_links)} nested links to crawl...", flush=True)
        sem = asyncio.Semaphore(3) # Max 3 concurrent headless browsers to avoid OOM
        tasks = [process_page(link, schema, sem) for link in nested_links]
        nested_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in nested_results:
            if isinstance(res, dict):
                results.append(res)
            elif isinstance(res, Exception):
                print(f"Spider task failed: {res}", flush=True)
                
    final_output = merge_json_outputs(results)
    return final_output
