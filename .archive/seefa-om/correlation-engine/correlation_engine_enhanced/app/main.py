"""Correlation Engine - Enhanced with MDSO integration"""
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
from app.routes import mdso as mdso_routes  # NEW
from app.pipeline.correlator import CorrelationEngine
from app.pipeline.exporters import ExporterManager
from app.mdso import MDSOClient, MDSOLogCollector  # NEW

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

REQUEST_COUNT = Counter('correlation_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('correlation_api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
LOG_RECORDS_RECEIVED = Counter('log_records_received_total', 'Total log records received', ['source'])
TRACES_RECEIVED = Counter('traces_received_total', 'Total traces received', ['source'])

correlation_engine: Optional[CorrelationEngine] = None
exporter_manager: Optional[ExporterManager] = None
mdso_client: Optional[MDSOClient] = None  # NEW
mdso_collector: Optional[MDSOLogCollector] = None  # NEW


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    global correlation_engine, exporter_manager, mdso_client, mdso_collector

    logger.info("Starting Correlation Engine", config=settings.dict())

    exporter_manager = ExporterManager(
        loki_url=settings.loki_url,
        tempo_grpc_endpoint=settings.tempo_grpc_endpoint,
        tempo_http_endpoint=settings.tempo_http_endpoint,
        datadog_api_key=settings.datadog_api_key,
        datadog_site=settings.datadog_site,
    )

    correlation_engine = CorrelationEngine(
        window_seconds=settings.corr_window_seconds,
        exporter_manager=exporter_manager,
    )
    
    app.state.correlation_engine = correlation_engine
    app.state.LOG_RECORDS_RECEIVED = LOG_RECORDS_RECEIVED
    app.state.TRACES_RECEIVED = TRACES_RECEIVED

    # NEW: Initialize MDSO client if enabled
    if settings.mdso_enabled and settings.mdso_url:
        logger.info("Initializing MDSO integration", url=settings.mdso_url)
        mdso_client = MDSOClient(
            base_url=settings.mdso_url,
            username=settings.mdso_user,
            password=settings.mdso_pass
        )
        mdso_collector = MDSOLogCollector(mdso_client)
        app.state.mdso_client = mdso_client
        app.state.mdso_collector = mdso_collector
        
        # Start scheduled MDSO collection
        mdso_task = asyncio.create_task(_run_mdso_collection())
    else:
        logger.info("MDSO integration disabled")
        mdso_task = None

    correlation_task = asyncio.create_task(correlation_engine.run())

    logger.info("Correlation Engine started")

    yield

    logger.info("Shutting down Correlation Engine")
    correlation_engine.stop()
    correlation_task.cancel()
    
    if mdso_task:
        mdso_task.cancel()
    
    try:
        await correlation_task
    except asyncio.CancelledError:
        pass
    
    if mdso_client:
        await mdso_client.close()
    
    await exporter_manager.close()
    logger.info("Correlation Engine stopped")


async def _run_mdso_collection():
    """Background task for scheduled MDSO collection"""
    if not mdso_collector:
        return
    
    products = [
        {"product_type": "service_mapper", "product_name": "ServiceMapper"},
        {"product_type": "network_service", "product_name": "NetworkService"},
        {"product_type": "disconnect_mapper", "product_name": "DisconnectMapper"},
    ]
    
    await mdso_collector.collect_scheduled(
        product_configs=products,
        interval_seconds=settings.mdso_collection_interval
    )


app = FastAPI(
    title="SEEFA Observability - Correlation Engine",
    description="Real-time log and trace correlation engine with MDSO integration",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=f"{duration:.3f}s",
    )
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(duration)
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


app.include_router(health.router, tags=["health"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(otlp.router, prefix="/api/otlp/v1", tags=["otlp"])
app.include_router(correlations.router, prefix="/api", tags=["correlations"])
app.include_router(mdso_routes.router, prefix="/api", tags=["mdso"])  # NEW


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return generate_latest()


@app.get("/")
async def root():
    return {
        "service": "correlation-engine",
        "version": "2.0.0",
        "mdso_enabled": settings.mdso_enabled,
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "logs": "/api/logs",
            "otlp_logs": "/api/otlp/v1/logs",
            "otlp_traces": "/api/otlp/v1/traces",
            "correlations": "/api/correlations",
            "mdso_collect": "/api/mdso/collect",
            "mdso_products": "/api/mdso/products",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, log_level=settings.log_level, reload=False)
