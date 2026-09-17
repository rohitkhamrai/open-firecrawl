import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import patch

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.asyncio
@patch('engine.fetcher._sync_fetch')
async def test_scrape_endpoint_no_schema(mock_fetch):
    mock_fetch.return_value = ("<html><body><h1>Test</h1><script>alert(1)</script></body></html>", {"status_code": 200, "url": "https://example.com"})
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/scrape", json={"url": "https://example.com"})
        
    assert response.status_code == 200
    data = response.json()
    assert "markdown" in data
    assert "Test" in data["markdown"]
    assert "alert" not in data["markdown"]
    assert data["json_data"] is None

@pytest.mark.asyncio
async def test_crawl_validation():
    # Test limits (maxDepth <= 5, limit <= 500)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/crawl", json={"url": "https://example.com", "maxDepth": 10, "limit": 1000})
        
    assert response.status_code == 422
