from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl, Field

class JsonOptions(BaseModel):
    schema_def: Optional[Dict[str, Any]] = Field(default=None, alias="schema")

class ScrapeRequest(BaseModel):
    url: HttpUrl
    schema_def: Dict[str, Any] = Field(..., alias="schema", description="JSON schema defining the structure to extract")
    limit: int = Field(default=10, le=500, description="Maximum URLs to crawl, hard limit 500")

class ScrapeResponse(BaseModel):
    markdown: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    json_data: Optional[Dict[str, Any]] = None

class CrawlRequest(BaseModel):
    url: HttpUrl
    maxDepth: int = Field(default=1, le=5, description="Maximum crawl depth, hard limit 5")
    limit: int = Field(default=10, le=500, description="Maximum URLs to crawl, hard limit 500")

class MapRequest(BaseModel):
    url: HttpUrl
