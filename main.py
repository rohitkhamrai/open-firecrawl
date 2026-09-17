from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
import json
from pydantic import BaseModel
import engine.db as db
from engine.crawler import crawl_domain

app = FastAPI(title="open-firecrawl")

@app.on_event("startup")
async def startup_event():
    await db.init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await db.close_db()

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>index.html not found</h1>"

@app.post("/scrape")
async def scrape_endpoint(url: str = Form(...), schema: str = Form(...)):
    try:
        schema_dict = json.loads(schema)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON schema"})
        
    try:
        # ponytail: Deep spider the root URL and save to Neon DB
        result = await crawl_domain(url, schema_dict)
        await db.save_scrape(url, result)
        
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
