from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
import asyncio

from api.schemas import ScrapeRequest, ScrapeResponse, CrawlRequest, MapRequest
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown
from engine.extractor import extract_schema
from engine.crawler import start_crawl, get_job_status, map_urls
import json

router = APIRouter()

@router.post("/v1/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):
    try:
        html, metadata = await fetch_page(str(request.url))
        markdown = clean_html_to_markdown(html)
        
        json_data = None
        if request.jsonOptions and request.jsonOptions.schema_def:
            json_data = await extract_schema(markdown, request.jsonOptions.schema_def)
            
        return ScrapeResponse(
            markdown=markdown,
            metadata=metadata,
            json_data=json_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/crawl")
async def crawl_endpoint(request: CrawlRequest):
    try:
        job_id = start_crawl(str(request.url), request.maxDepth, request.limit)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/crawl/{job_id}")
async def crawl_status_endpoint(job_id: str, request: Request):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if request.headers.get("accept") != "text/event-stream":
        return status
        
    async def sse_generator():
        while True:
            if await request.is_disconnected():
                break
                
            current_status = get_job_status(job_id)
            if not current_status:
                yield {"data": json.dumps({"error": "Job not found or expired"})}
                break
                
            # Serialize carefully due to possible complex dicts
            yield {"data": json.dumps(current_status, default=str)}
            
            if current_status["status"] in ("completed", "failed"):
                break
                
            await asyncio.sleep(1)
            
    return EventSourceResponse(sse_generator())

@router.post("/v1/map")
async def map_endpoint(request: MapRequest):
    try:
        links = await map_urls(str(request.url))
        return {"links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
