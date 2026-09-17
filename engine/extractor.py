import json
import asyncio
from typing import Dict, Any, List, Optional
import httpx
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
        
    merged = {}
    # Initialize keys from the first result
    for key in results[0].keys():
        val_type = type(results[0][key])
        if val_type is list:
            merged[key] = []
        elif val_type is dict:
            merged[key] = {}
        else:
            merged[key] = ""

    for res in results:
        for k, v in res.items():
            if k not in merged:
                continue
                
            if isinstance(v, list):
                # Deduplicate based on exact match of dicts or items
                for item in v:
                    if item not in merged[k]:
                        merged[k].append(item)
            elif isinstance(v, dict):
                # We could recurse, but top level properties are usually enough
                merged[k].update(v)
            else:
                # Keep the first non-empty value
                if not merged[k] and v:
                    merged[k] = v
                    
    return merged

class ResourcePool:
    def __init__(self, groq_key: str, or_key: str):
        self.groq_key = groq_key
        self.or_key = or_key
        self.models = []
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        if self.groq_key:
            self.models.append(("groq", settings.DEFAULT_MODEL))
            
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
                                self.models.append(("openrouter", m_id))
            except Exception as e:
                print(f"Failed to fetch OpenRouter free models: {e}")
                
        if not self.models:
            raise ValueError("No free models available across Groq or OpenRouter")
            
    async def acquire_model(self) -> tuple[str, str]:
        async with self._lock:
            if not self.models:
                raise RuntimeError("ResourcePool depleted: all free models failed.")
            return self.models.pop(0)
            
    async def release_model(self, provider: str, model_id: str):
        async with self._lock:
            self.models.append((provider, model_id))

async def _extract_chunk(client: Any, chunk: str, schema: Dict[str, Any], provider: str, model_id: str) -> Optional[Dict[str, Any]]:
    prompt = f"""
You are an expert data extractor. Extract information from the provided Markdown text into a strict JSON object that matches the exact JSON schema provided.
Do NOT include any markdown formatting blocks like ```json in your response. Output raw JSON only.

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

async def _extract_with_retry(pool: ResourcePool, chunk: str, schema: Dict[str, Any], or_client: Any, groq_client: Any) -> Optional[Dict[str, Any]]:
    max_retries = 3
    for _ in range(max_retries):
        provider, model_id = await pool.acquire_model()
        try:
            client = or_client if provider == "openrouter" else groq_client
            print(f"Extracting chunk on {provider}/{model_id}...", flush=True)
            res = await _extract_chunk(client, chunk, schema, provider, model_id)
            if res is not None:
                await pool.release_model(provider, model_id) # Release on success
                return res
        except Exception as e:
            print(f"Chunk extraction failed on {provider}/{model_id}: {str(e)}", flush=True)
            # Do NOT release the model on failure so it is permanently removed from rotation
            
    return None

async def extract_schema(markdown: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    or_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY, timeout=30.0) if settings.OPENROUTER_API_KEY else None
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=30.0) if settings.GROQ_API_KEY else None
    
    pool = ResourcePool(settings.GROQ_API_KEY, settings.OPENROUTER_API_KEY)
    await pool.initialize()
        
    chunks = chunk_markdown(markdown)
    tasks = []
    
    for chunk in chunks:
        tasks.append(_extract_with_retry(pool, chunk, schema, or_client, groq_client))
        
    results = await asyncio.gather(*tasks)
    
    # Filter out None results
    valid_results = [r for r in results if r is not None]
    
    if not valid_results:
        return None
        
    return valid_results[0] if len(valid_results) == 1 else merge_json_outputs(valid_results)
