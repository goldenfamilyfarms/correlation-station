"""
Correlation Engine - FastAPI Application
Accepts logs and OTLP telemetry, correlates by trace_id, exports to Loki/Tempo/Prometheus
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
import structlog

from app.config import settings
from app.routes import health, logs, otlp, correlations
from app.pipeline.correlator import CorrelationEngine
from app.pipeline.exporters import ExporterManager

# Import observability for self-monitoring
try:
    from app.observability import setup_observability
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logging.warning("OpenTelemetry instrumentation not available")

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_level == "info" else structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'correlation_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'correlation_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)
LOG_RECORDS_RECEIVED = Counter(
    'log_records_received_total',
    'Total log records received',
    ['source']
)
TRACES_RECEIVED = Counter(
    'traces_received_total',
    'Total traces received',
    ['source']
)

# Global instances
correlation_engine: Optional[CorrelationEngine] = None
exporter_manager: Optional[ExporterManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    global correlation_engine, exporter_manager

    logger.info("Starting Correlation Engine", config=settings.dict())

    # Initialize exporters
    exporter_manager = ExporterManager(
        loki_url=settings.loki_url,
        tempo_grpc_endpoint=settings.tempo_grpc_endpoint,
        tempo_http_endpoint=settings.tempo_http_endpoint,
        datadog_api_key=settings.datadog_api_key,
        datadog_site=settings.datadog_site,
    )

    # Initialize correlation engine
    correlation_engine = CorrelationEngine(
        window_seconds=settings.corr_window_seconds,
        exporter_manager=exporter_manager,
    )
    
    # Store in app state
    app.state.correlation_engine = correlation_engine
    app.state.LOG_RECORDS_RECEIVED = LOG_RECORDS_RECEIVED
    app.state.TRACES_RECEIVED = TRACES_RECEIVED

    # Start background correlation task
    correlation_task = asyncio.create_task(correlation_engine.run())

    logger.info("Correlation Engine started")

    yield

    # Shutdown - proper cleanup with single close() call
    logger.info("Shutting down Correlation Engine")
    correlation_engine.stop()

    # Cancel background task
    correlation_task.cancel()

    try:
        # Wait for task to complete cancellation
        await correlation_task
    except asyncio.CancelledError:
        logger.info("Correlation task cancelled successfully")
    except Exception as e:
        logger.exception("Error during correlation task shutdown", error=str(e))
    finally:
        # Ensure exporter cleanup happens exactly once
        try:
            await exporter_manager.close()
            logger.info("Exporters closed successfully")
        except Exception as e:
            logger.exception("Error closing exporters", error=str(e))

        logger.info("Correlation Engine stopped")


# Create FastAPI app
app = FastAPI(
    title="SEEFA Observability - Correlation Engine",
    description="""Real-time log and trace correlation engine for SEEFA Observability Platform.
    
    ## Features
    - **Real-time Correlation**: Links logs and traces within 60s windows using trace_id
    - **Multi-Backend Export**: Exports to Loki, Tempo, Prometheus, and optional Datadog
    - **OTLP Support**: Native OpenTelemetry Protocol ingestion
    - **Low-Cardinality Design**: Prevents metric explosion with optimized labeling
    
    ## Endpoints
    - **POST /api/logs**: Ingest log batches
    - **POST /api/otlp/v1/logs**: OTLP logs ingestion
    - **POST /api/otlp/v1/traces**: OTLP traces ingestion
    - **GET /api/correlations**: Query correlation events
    - **POST /api/events**: Inject synthetic correlation events
    - **GET /health**: Health check
    - **GET /metrics**: Prometheus metrics
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "SEEFA Observability Team",
        "email": "observability@seefa.com",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== SELF-OBSERVABILITY =====
# Instrument correlation engine to monitor itself
# Exports directly to Tempo/DataDog (NOT to self) to avoid infinite loops
if OTEL_AVAILABLE and settings.enable_self_observability:
    try:
        setup_observability(
            app,
            service_name="correlation-engine",
            service_version="1.0.0",
            environment=settings.deployment_env,
            tempo_grpc_endpoint=settings.tempo_grpc_endpoint,
            datadog_enabled=settings.self_observability_datadog_enabled,
            enable_metrics=True,
            metric_export_interval_ms=settings.self_observability_metric_interval_ms,
        )
        logger.info("Correlation Engine self-observability enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize self-observability: {e}")
else:
    logger.info("Self-observability disabled or unavailable")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and track metrics"""
    import time
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log request
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=f"{duration:.3f}s",
    )

    # Track metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(otlp.router, prefix="/api/otlp/v1", tags=["otlp"])
app.include_router(correlations.router, prefix="/api", tags=["correlations"])


# Prometheus metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "correlation-engine",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "logs": "/api/logs",
            "otlp_logs": "/api/otlp/v1/logs",
            "otlp_traces": "/api/otlp/v1/traces",
            "correlations": "/api/correlations",
            "events": "/api/events",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )