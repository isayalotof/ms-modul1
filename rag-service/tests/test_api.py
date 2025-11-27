import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "rag-service"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "dependencies" in data


@pytest.mark.asyncio
async def test_search_invalid_request():
    """Test search with invalid request"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/search",
            json={"query": "test"}  # Missing user_id
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_rag_query_invalid_request():
    """Test RAG query with invalid request"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/query",
            json={"query": "test"}  # Missing user_id
        )
        assert response.status_code == 422  # Validation error
