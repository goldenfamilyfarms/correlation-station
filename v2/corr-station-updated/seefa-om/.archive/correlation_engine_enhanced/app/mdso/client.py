"""MDSO API client with OpenTelemetry instrumentation"""
import json
import structlog
from typing import List, Dict, Any, Optional
import httpx
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .models import MDSOResource, MDSOOrchTrace

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class MDSOClient:
    """Async MDSO API client"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(verify=False, timeout=30.0)
    
    async def get_token(self) -> str:
        """Get authentication token from MDSO"""
        with tracer.start_as_current_span("mdso.get_token") as span:
            if self._token:
                return self._token
            
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            body = {"username": self.username, "password": self.password, "tenant": "master"}
            
            try:
                response = await self._client.post(
                    f"{self.base_url}/tron/api/v1/tokens",
                    json=body,
                    headers=headers
                )
                response.raise_for_status()
                self._token = response.json()["token"]
                span.set_attribute("mdso.token_acquired", True)
                logger.info("mdso_token_acquired")
                return self._token
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error("mdso_token_failed", error=str(e))
                raise
    
    async def delete_token(self):
        """Delete authentication token"""
        if not self._token:
            return
        
        with tracer.start_as_current_span("mdso.delete_token"):
            headers = {"Authorization": f"Bearer {self._token}"}
            try:
                await self._client.delete(
                    f"{self.base_url}/tron/api/v1/tokens/{self._token}",
                    headers=headers
                )
                self._token = None
                logger.info("mdso_token_deleted")
            except Exception as e:
                logger.warning("mdso_token_delete_failed", error=str(e))
    
    async def get_resources(
        self, 
        product_name: str, 
        limit: Optional[int] = None
    ) -> List[MDSOResource]:
        """Get resources by product type"""
        with tracer.start_as_current_span(
            "mdso.get_resources",
            attributes={"mdso.product_name": product_name}
        ) as span:
            token = await self.get_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            resource_type = f"charter.resourceTypes.{product_name}"
            
            # Get count
            count_url = f"{self.base_url}/bpocore/market/api/v1/resources/count?exactTypeId={resource_type}"
            count_resp = await self._client.get(count_url, headers=headers)
            count_resp.raise_for_status()
            total_count = count_resp.json()["count"]
            
            span.set_attribute("mdso.total_count", total_count)
            
            # Get resources
            fetch_limit = limit or total_count
            url = f"{self.base_url}/bpocore/market/api/v1/resources?resourceTypeId={resource_type}&limit={fetch_limit}"
            
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
            
            items = response.json()["items"]
            span.set_attribute("mdso.fetched_count", len(items))
            
            resources = [MDSOResource(**item) for item in items]
            logger.info("mdso_resources_fetched", product=product_name, count=len(resources))
            
            return resources
    
    async def get_orch_trace(
        self, 
        circuit_id: str, 
        resource_id: str
    ) -> Optional[MDSOOrchTrace]:
        """Get orchestration trace for a circuit"""
        with tracer.start_as_current_span(
            "mdso.get_orch_trace",
            attributes={
                "mdso.circuit_id": circuit_id,
                "mdso.resource_id": resource_id
            }
        ) as span:
            token = await self.get_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            resource_type = "tosca.resourceTypes.TraceLog"
            orch_name = f"{circuit_id}.orch_trace"
            
            url = f"{self.base_url}/bpocore/market/api/v1/resources?resourceTypeId={resource_type}&p=label:{orch_name}&limit=10"
            
            try:
                response = await self._client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if not data.get("items"):
                    span.set_attribute("mdso.orch_trace_found", False)
                    return None
                
                trace_item = data["items"][0]
                orch_trace = trace_item.get("properties", {}).get("orchestration_trace", [])
                
                span.set_attribute("mdso.orch_trace_found", True)
                span.set_attribute("mdso.trace_steps", len(orch_trace))
                
                return MDSOOrchTrace(
                    circuit_id=circuit_id,
                    resource_id=resource_id,
                    trace_data=orch_trace,
                    timestamp=trace_item["createdAt"]
                )
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error("mdso_orch_trace_failed", circuit_id=circuit_id, error=str(e))
                return None
    
    async def close(self):
        """Close client connection"""
        await self.delete_token()
        await self._client.aclose()
