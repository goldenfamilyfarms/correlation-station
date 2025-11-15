"""Tests for health check endpoints"""
import pytest
import asyncio
from datetime import datetime
from httpx import AsyncClient
from app.main import app


class TestHealthEndpoint:
    """Test health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self):
        """Health endpoint should return 200 OK"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_returns_json(self):
        """Health endpoint should return JSON response"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_check_has_status_field(self):
        """Health response should have status field"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_has_version(self):
        """Health response should have version field"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    @pytest.mark.asyncio
    async def test_health_check_has_timestamp(self):
        """Health response should have timestamp field"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        data = response.json()
        assert "timestamp" in data
        # Validate timestamp format
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_health_check_has_components(self):
        """Health response should have components field"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        data = response.json()
        assert "components" in data
        assert isinstance(data["components"], dict)

    @pytest.mark.asyncio
    async def test_health_check_components_are_healthy(self):
        """All components should report as healthy"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        data = response.json()
        components = data["components"]

        assert "api" in components
        assert components["api"] == "healthy"
        assert "correlator" in components
        assert components["correlator"] == "healthy"
        assert "exporters" in components
        assert components["exporters"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_multiple_calls(self):
        """Health endpoint should handle multiple concurrent calls"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            responses = await asyncio.gather(*[
                client.get("/health")
                for _ in range(10)
            ])

        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_health_check_timestamps_increase(self):
        """Timestamps should increase with each call"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response1 = await client.get("/health")
            await asyncio.sleep(0.1)
            response2 = await client.get("/health")

        time1 = datetime.fromisoformat(response1.json()["timestamp"].replace("Z", "+00:00"))
        time2 = datetime.fromisoformat(response2.json()["timestamp"].replace("Z", "+00:00"))

        assert time2 >= time1
