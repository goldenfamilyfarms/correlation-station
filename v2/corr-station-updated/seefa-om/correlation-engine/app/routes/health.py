"""Health check endpoint"""
from datetime import datetime
from fastapi import APIRouter
from app.models import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        components={
            "api": "healthy",
            "correlator": "healthy",
            "exporters": "healthy",
        }
    )