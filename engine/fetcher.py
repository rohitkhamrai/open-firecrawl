import asyncio
from scrapling import StealthyFetcher
from typing import Dict, Any, Tuple

def _sync_fetch(url: str) -> Tuple[str, Dict[str, Any]]:
    page = StealthyFetcher.fetch(url)
    
    metadata = {
        "status_code": page.status,
        "url": page.url
    }
    
    html = page.body.decode('utf-8', errors='ignore')
    return html, metadata

async def fetch_page(url: str) -> Tuple[str, Dict[str, Any]]:
    # Run stealth fetcher in a separate thread to avoid blocking the event loop
    return await asyncio.to_thread(_sync_fetch, url)
