"""Health check endpoints with Kubernetes liveness/readiness probes"""
from datetime import datetime
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from app.models import HealthStatus
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint (legacy)"""
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


@router.get("/health/live")
async def liveness():
    """
    Kubernetes liveness probe - is the application process running?

    This endpoint should return 200 if the application is alive,
    even if it's not ready to serve traffic.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "process": "running"
        }
    }


@router.get("/health/ready")
async def readiness(request: Request):
    """
    Kubernetes readiness probe - can the application serve traffic?

    This endpoint checks:
    - Redis connection (if enabled)
    - Correlation engine state
    - Exporter availability

    Returns 200 if ready, 503 if not ready.
    """
    checks = {}
    all_healthy = True

    # Check correlation engine
    try:
        correlation_engine = request.app.state.correlation_engine
        if correlation_engine and correlation_engine.running:
            checks["correlation_engine"] = "running"
        else:
            checks["correlation_engine"] = "not_running"
            all_healthy = False
    except Exception as e:
        checks["correlation_engine"] = f"error: {str(e)}"
        all_healthy = False

    # Check Redis connection (if using Redis state)
    try:
        if hasattr(correlation_engine, 'state_manager'):
            state_manager = correlation_engine.state_manager

            # Check if it's RedisStateManager
            if hasattr(state_manager, 'redis') and state_manager.redis:
                try:
                    await state_manager.redis.ping()
                    checks["redis"] = "connected"
                except Exception as e:
                    checks["redis"] = f"connection_failed: {str(e)}"
                    all_healthy = False
                    logger.error("Redis health check failed", error=str(e))
            else:
                # In-memory state manager
                checks["state_backend"] = "in-memory"
    except Exception as e:
        checks["state"] = f"error: {str(e)}"
        logger.error("State manager health check failed", error=str(e))

    # Check exporters
    try:
        exporter_manager = request.app.state.correlation_engine.exporter_manager
        if exporter_manager:
            checks["exporters"] = "initialized"
        else:
            checks["exporters"] = "not_initialized"
            all_healthy = False
    except Exception as e:
        checks["exporters"] = f"error: {str(e)}"
        all_healthy = False

    # Return appropriate status code
    if all_healthy:
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks
            }
        )


@router.get("/health/startup")
async def startup(request: Request):
    """
    Kubernetes startup probe - has the application finished starting up?

    This is useful for slow-starting applications. Returns 200 when
    startup is complete.
    """
    checks = {}

    # Check if correlation engine is initialized
    try:
        correlation_engine = request.app.state.correlation_engine
        if correlation_engine:
            checks["correlation_engine"] = "initialized"
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "starting",
                    "timestamp": datetime.utcnow().isoformat(),
                    "checks": {"correlation_engine": "not_initialized"}
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "starting",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {"error": str(e)}
            }
        )

    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }