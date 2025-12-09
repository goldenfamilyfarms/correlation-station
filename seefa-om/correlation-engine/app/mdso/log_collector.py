"""MDSO log collector with OpenTelemetry spans"""
import asyncio
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union
import pendulum
from opentelemetry import trace, baggage

from .client import MDSOClient
from .models import MDSOResource, MDSOError
from .repository import MDSORepository, HTTPMDSORepository

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class MDSOLogCollector:
    """Collects logs from MDSO with distributed tracing

    Now supports both MDSOClient (legacy) and MDSORepository (new pattern).
    Using repository pattern enables better testing and abstraction.
    """

    def __init__(self, mdso_source: Union[MDSOClient, MDSORepository]):
        """Initialize with either MDSOClient or MDSORepository

        Args:
            mdso_source: Either MDSOClient (legacy) or MDSORepository (preferred)
        """
        # Support both client and repository for backward compatibility
        if isinstance(mdso_source, MDSORepository):
            self.mdso_repo = mdso_source
            self.mdso_client = None  # Deprecated
        else:
            # Wrap client in repository for consistent interface
            self.mdso_repo = HTTPMDSORepository(mdso_source)
            self.mdso_client = mdso_source  # Keep for backward compatibility
    
    async def collect_product_logs(
        self,
        product_type: str,
        product_name: str,
        time_range_hours: int = 3
    ) -> List[Dict[str, Any]]:
        """Collect logs for a product type with tracing"""
        with tracer.start_as_current_span(
            "mdso.collect_product_logs",
            attributes={
                "mdso.product_type": product_type,
                "mdso.product_name": product_name,
                "mdso.time_range_hours": time_range_hours,
            }
        ) as span:
            now = pendulum.now("UTC")
            date_start = now.subtract(hours=time_range_hours)
            
            span.set_attribute("mdso.date_start", date_start.to_iso8601_string())

            # Get resources from MDSO via repository
            resources = await self.mdso_repo.get_resources(product_name)
            
            # Filter by time range
            filtered = [
                r for r in resources 
                if r.created_at >= date_start.to_datetime_string()
            ]
            
            span.set_attribute("mdso.filtered_count", len(filtered))
            logger.info(
                "mdso_resources_filtered",
                product=product_name,
                total=len(resources),
                filtered=len(filtered)
            )
            
            # Process each circuit
            logs = []
            for resource in filtered:
                circuit_logs = await self._process_circuit(resource, product_type)
                logs.extend(circuit_logs)
            
            span.set_attribute("mdso.logs_collected", len(logs))
            return logs
    
    async def _process_circuit(
        self,
        resource: MDSOResource,
        product_type: str
    ) -> List[Dict[str, Any]]:
        """Process a single circuit with baggage propagation"""
        circuit_id = resource.circuit_id or resource.label or "unknown"
        
        # Set baggage for context propagation
        ctx = baggage.set_baggage("circuit_id", circuit_id)
        ctx = baggage.set_baggage("product_type", product_type, context=ctx)
        ctx = baggage.set_baggage("resource_id", resource.id, context=ctx)
        
        with tracer.start_as_current_span(
            "mdso.process_circuit",
            context=ctx,
            attributes={
                "mdso.circuit_id": circuit_id,
                "mdso.resource_id": resource.id,
                "mdso.orch_state": resource.orch_state,
            }
        ) as span:
            logs = []

            # Get orchestration trace via repository
            orch_trace = await self.mdso_repo.get_orch_trace(circuit_id, resource.id)
            
            if orch_trace:
                errors = orch_trace.get_errors()
                span.set_attribute("mdso.errors_found", len(errors))
                
                for error in errors:
                    log_entry = {
                        "timestamp": orch_trace.timestamp.isoformat(),
                        "circuit_id": circuit_id,
                        "resource_id": resource.id,
                        "product_type": product_type,
                        "error": error["error"],
                        "process": error.get("process"),
                        "resource_type": error.get("resource_type"),
                        "orch_state": resource.orch_state,
                        "device_tid": resource.device_tid,
                    }
                    logs.append(log_entry)
                    
                    # Add span event for each error
                    span.add_event(
                        "mdso.error_detected",
                        attributes={
                            "error.message": error["error"][:200],
                            "error.process": error.get("process", "unknown"),
                        }
                    )
            
            return logs
    
    async def collect_scheduled(
        self,
        product_configs: List[Dict[str, Any]],
        interval_seconds: int = 3600
    ):
        """Run scheduled collection for multiple products"""
        with tracer.start_as_current_span("mdso.scheduled_collection") as span:
            span.set_attribute("mdso.interval_seconds", interval_seconds)
            span.set_attribute("mdso.product_count", len(product_configs))
            
            while True:
                try:
                    for config in product_configs:
                        await self.collect_product_logs(
                            product_type=config["product_type"],
                            product_name=config["product_name"],
                            time_range_hours=config.get("time_range_hours", 3)
                        )
                    
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    logger.error("mdso_scheduled_collection_error", error=str(e))
                    await asyncio.sleep(60)
