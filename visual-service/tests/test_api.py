"""Tests for API endpoints."""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "visual-service"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "dependencies" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_images_generated" in data
    assert "total_charts_generated" in data


@pytest.mark.asyncio
async def test_generate_chart_line(client):
    """Test line chart generation."""
    request_data = {
        "chart_type": "line",
        "data": {
            "x": [1, 2, 3, 4, 5],
            "y": [10, 15, 13, 18, 20],
        },
        "title": "Test Chart",
        "user_id": "test_user",
    }

    response = await client.post("/api/v1/visual/generate-chart", json=request_data)

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "chart_url" in data
        assert "chart_key" in data
        assert data["metadata"]["chart_type"] == "line"


@pytest.mark.asyncio
async def test_generate_chart_invalid_type(client):
    """Test chart generation with invalid type."""
    request_data = {
        "chart_type": "invalid_type",
        "data": {
            "y": [10, 15, 13, 18, 20],
        },
        "user_id": "test_user",
    }

    response = await client.post("/api/v1/visual/generate-chart", json=request_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_generate_image(client):
    """Test image generation."""
    request_data = {
        "prompt": "A beautiful sunset",
        "style": "realistic",
        "size": "1024x1024",
        "user_id": "test_user",
    }

    response = await client.post("/api/v1/visual/generate-image", json=request_data)

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "image_url" in data
        assert "image_key" in data


@pytest.mark.asyncio
async def test_generate_chart_from_code(client):
    """Test chart generation from code."""
    code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('X')
plt.ylabel('Y')
plt.savefig(filepath)
"""

    request_data = {
        "code": code,
        "user_id": "test_user",
    }

    response = await client.post("/api/v1/visual/generate-chart-from-code", json=request_data)

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "chart_url" in data
