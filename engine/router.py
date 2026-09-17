import json
import urllib.parse
from typing import List
from openai import AsyncOpenAI
from config import settings

async def rank_urls(links: List[str], limit: int) -> List[str]:
    """Stage 1: LLM Link Router. Filters and ranks links to find high-value pages."""
    if not links:
        return []
        
    or_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY, timeout=30.0) if settings.OPENROUTER_API_KEY else None
    
    prompt = f"""You are a URL router for a web crawler. 
Given the following list of URLs, identify which ones are most likely to contain product details, pricing, specific pooja offerings, or blog posts.
Filter out all utility links (like /about, /contact, /login, /terms, /privacy, etc.) and category/header links.
Rank the remaining URLs by importance and return ONLY a JSON array of strings containing the top {limit} URLs. Do not include any other text, markdown formatting, or explanations. Just the JSON array.

URLs:
{chr(10).join(links)}
"""
    
    try:
        if not or_client:
            raise ValueError("No OpenRouter client available")
        # Use a fast free model for routing
        response = await or_client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content
        # Clean up markdown if any
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        ranked_links = json.loads(content.strip())
        if isinstance(ranked_links, list):
            # Ensure we only return strings and max 'limit'
            return [str(link) for link in ranked_links][:limit]
    except Exception as e:
        print(f"Failed to route URLs with LLM: {str(e)}", flush=True)
        
    # Fallback heuristic if LLM fails
    print("Falling back to path length heuristic", flush=True)
    def rank_url(u: str) -> int:
        score = len(urllib.parse.urlparse(u).path)
        if 'puja' in u.lower() or 'epuja' in u.lower() or 'temple' in u.lower() or 'blog' in u.lower():
            score += 1000
        return score
    return sorted(list(links), key=rank_url, reverse=True)[:limit]
