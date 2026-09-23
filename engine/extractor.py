import json
import asyncio
from typing import Dict, Any, List, Optional
import httpx
import urllib.parse
from groq import AsyncGroq
from openai import AsyncOpenAI
from config import settings

def chunk_markdown(markdown: str, chunk_size: int = 12000, overlap: int = 1000) -> List[str]:
    """Splits markdown into chunks with an overlap."""
    if len(markdown) <= chunk_size:
        return [markdown]
        
    chunks = []
    start = 0
    while start < len(markdown):
        end = min(start + chunk_size, len(markdown))
        chunks.append(markdown[start:end])
        if end == len(markdown):
            break
        start += chunk_size - overlap
    return chunks

def merge_json_outputs(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Recursively merges a list of JSON objects."""
    if not results:
        return {}
        
    def is_empty_value(val: Any) -> bool:
        if not val:
            return True
        if isinstance(val, str):
            lower_val = val.lower()
            empty_phrases = ["unknown", "not mentioned", "not provided", "n/a", "no data", "none"]
            if any(phrase in lower_val for phrase in empty_phrases) or len(val.strip()) < 2:
                return True
        return False
        
    def recursive_merge(base: Any, new_val: Any) -> Any:
        if isinstance(base, dict) and isinstance(new_val, dict):
            for k, v in new_val.items():
                if k not in base:
                    base[k] = v
                else:
                    base[k] = recursive_merge(base[k], v)
            return base
        elif isinstance(base, list) and isinstance(new_val, list):
            for item in new_val:
                if is_empty_value(item):
                    continue
                # If item is a dict, see if we can merge it with an existing dict in base
                if isinstance(item, dict):
                    # Identify a primary key (name, source, post_url, title, etc.)
                    primary_keys = ['name', 'source', 'post_url', 'title', 'url']
                    key_field = next((k for k in primary_keys if k in item), None)
                    
                    merged = False
                    if key_field and item[key_field]:
                        # Look for existing item with same key
                        for existing in base:
                            if isinstance(existing, dict) and existing.get(key_field) == item[key_field]:
                                recursive_merge(existing, item)
                                merged = True
                                break
                                
                    if not merged and item not in base:
                        base.append(item)
                elif item not in base:
                    base.append(item)
            return base
        else:
            # For primitives (strings, ints), prefer the one that is NOT empty/unknown
            if is_empty_value(base) and not is_empty_value(new_val):
                return new_val
            elif not is_empty_value(base) and not is_empty_value(new_val):
                # If both have data, prefer the longer one (more detail)
                if isinstance(base, str) and isinstance(new_val, str) and len(new_val) > len(base):
                    return new_val
            return base

    merged = {}
    for res in results:
        merged = recursive_merge(merged, res)
                    
    return merged

class ResourcePool:
    def __init__(self, groq_keys: list[str], or_key: str):
        self.groq_keys = groq_keys
        self.or_key = or_key
        self.models = asyncio.Queue()
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        for key in self.groq_keys:
            await self.models.put(("groq", settings.DEFAULT_MODEL, key.strip()))
            
        if self.or_key:
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get("https://openrouter.ai/api/v1/models", timeout=10.0)
                    if res.status_code == 200:
                        data = res.json().get("data", [])
                        for m in data:
                            m_id = m["id"]
                            prompt_price = m.get("pricing", {}).get("prompt", "0")
                            if prompt_price == "0" or m_id.endswith(":free"):
                                await self.models.put(("openrouter", m_id, self.or_key))
            except Exception as e:
                print(f"Failed to fetch OpenRouter free models: {e}")
                
        if self.models.empty():
            raise ValueError("No free models available across Groq or OpenRouter")
            
    async def acquire_model(self) -> tuple[str, str, str]:
        return await self.models.get()
            
    async def release_model(self, provider: str, model_id: str, api_key: str):
        await self.models.put((provider, model_id, api_key))

async def _extract_chunk(client: Any, chunk: str, schema: Dict[str, Any], provider: str, model_id: str) -> Optional[Dict[str, Any]]:
    prompt = f"""
You are an expert data extractor. Extract information from the provided Markdown text into a strict JSON object that matches the exact JSON schema provided.
Do NOT include any markdown formatting blocks like ```json in your response. Output raw JSON only.
CRITICAL: If the markdown contains a [SYSTEM META: Post Engagement Metrics] block at the top, you MUST use it to populate the social_media_traction fields.
CRITICAL: If a social media URL is present (e.g., in a `## Source:` header), you MUST add it to the `top_posts` array. Extract likes and views directly from the Search Snippet text in the [SYSTEM META] block (e.g., look for '1.5M views' or '10 likes'). NEVER output 'Unknown' if the metric is visible anywhere in the text!

JSON Schema:
{json.dumps(schema, indent=2)}

Markdown Text:
{chunk}
"""
    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a precise data extraction API that only responds with valid JSON objects matching the user's schema."},
            {"role": "user", "content": prompt}
        ],
        model=model_id,
        response_format={"type": "json_object"} if provider == "openrouter" else {"type": "json_object"},
        temperature=0.0,
    )
        
    content = response.choices[0].message.content
    if not content:
        return None
        
    # Clean up possible markdown wrappers if the model still includes them
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
        
    return json.loads(content.strip())

async def _extract_with_retry(pool: ResourcePool, chunk: str, schema: Dict[str, Any], or_client: Any, groq_clients: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    max_retries = 3
    for _ in range(max_retries):
        provider, model_id, api_key = await pool.acquire_model()
        try:
            client = or_client if provider == "openrouter" else groq_clients[api_key]
            print(f"Extracting chunk on {provider}/{model_id}...", flush=True)
            res = await asyncio.wait_for(_extract_chunk(client, chunk, schema, provider, model_id), timeout=60.0)
            if res is not None:
                await pool.release_model(provider, model_id, api_key) # Release on success
                return res
        except asyncio.TimeoutError:
            print(f"Chunk extraction failed on {provider}/{model_id}: Hard timeout exceeded (60s)", flush=True)
            # Re-enqueue the model — timeout is transient, not a permanent failure
            await pool.release_model(provider, model_id, api_key)
        except Exception as e:
            print(f"Chunk extraction failed on {provider}/{model_id}: {str(e)}", flush=True)
            # Always re-enqueue to prevent Queue deadlocks
            await pool.release_model(provider, model_id, api_key)
            
    return None

async def extract_schema(markdown: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    or_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY, timeout=65.0) if settings.OPENROUTER_API_KEY else None
    groq_clients = {key.strip(): AsyncGroq(api_key=key.strip(), timeout=65.0) for key in settings.groq_keys}
    
    pool = ResourcePool(settings.groq_keys, settings.OPENROUTER_API_KEY)
    await pool.initialize()
        
    chunks = chunk_markdown(markdown)
    tasks = []
    
    for chunk in chunks:
        tasks.append(_extract_with_retry(pool, chunk, schema, or_client, groq_clients))
        
    results = await asyncio.gather(*tasks)
    
    # Filter out None results
    valid_results = [r for r in results if r is not None]
    
    if not valid_results:
        return None
        
    return valid_results[0] if len(valid_results) == 1 else merge_json_outputs(valid_results)
