"""MDSO-specific API endpoints"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from app.mdso import MDSOClient, MDSOLogCollector, MDSOErrorAnalyzer

logger = structlog.get_logger()
router = APIRouter()


class MDSOCollectionRequest(BaseModel):
    product_type: str
    product_name: str
    time_range_hours: int = 3


class MDSOCollectionResponse(BaseModel):
    status: str
    message: str
    logs_collected: int
    errors_found: int


@router.post("/mdso/collect", response_model=MDSOCollectionResponse)
async def trigger_mdso_collection(
    request: MDSOCollectionRequest,
    background_tasks: BackgroundTasks
):
    """Trigger MDSO log collection for a product"""
    try:
        # Get MDSO client from app state (initialized in main.py)
        from app.main import app
        mdso_client = getattr(app.state, "mdso_client", None)
        
        if not mdso_client:
            raise HTTPException(status_code=503, detail="MDSO client not initialized")
        
        collector = MDSOLogCollector(mdso_client)
        analyzer = MDSOErrorAnalyzer()
        
        # Collect logs
        logs = await collector.collect_product_logs(
            product_type=request.product_type,
            product_name=request.product_name,
            time_range_hours=request.time_range_hours
        )
        
        # Analyze errors
        errors = analyzer.analyze_errors(logs)
        
        logger.info(
            "mdso_collection_triggered",
            product=request.product_name,
            logs=len(logs),
            errors=len(errors)
        )
        
        return MDSOCollectionResponse(
            status="success",
            message=f"Collected logs for {request.product_name}",
            logs_collected=len(logs),
            errors_found=len(errors)
        )
    except Exception as e:
        logger.error("mdso_collection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mdso/products")
async def list_mdso_products():
    """List available MDSO products for collection"""
    return {
        "products": [
            {
                "product_type": "service_mapper",
                "product_name": "ServiceMapper",
                "description": "Service Mapper product logs"
            },
            {
                "product_type": "network_service",
                "product_name": "NetworkService",
                "description": "Network Service product logs"
            },
            {
                "product_type": "disconnect_mapper",
                "product_name": "DisconnectMapper",
                "description": "Disconnect Mapper product logs"
            },
            {
                "product_type": "network_service_update",
                "product_name": "NetworkServiceUpdate",
                "description": "Network Service Update product logs"
            }
        ]
    }


@router.get("/mdso/status")
async def mdso_status():
    """Get MDSO integration status"""
    from app.main import app
    mdso_client = getattr(app.state, "mdso_client", None)
    
    return {
        "mdso_enabled": mdso_client is not None,
        "status": "connected" if mdso_client else "disconnected"
    }
