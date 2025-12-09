"""MDSO data models"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class MDSOResource(BaseModel):
    """MDSO resource representation"""
    id: str
    label: Optional[str] = None
    resource_type_id: str
    product_id: Optional[str] = None
    orch_state: Optional[str] = None
    created_at: datetime
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def circuit_id(self) -> Optional[str]:
        return self.properties.get("circuit_id")
    
    @property
    def device_tid(self) -> Optional[str]:
        return self.properties.get("device_tid")


class MDSOOrchTrace(BaseModel):
    """MDSO orchestration trace"""
    circuit_id: str
    resource_id: str
    trace_data: List[Dict[str, Any]]
    timestamp: datetime
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Extract errors from trace"""
        errors = []
        for trace in self.trace_data:
            if trace.get("categorized_error"):
                errors.append({
                    "error": trace["categorized_error"],
                    "process": trace.get("process"),
                    "resource_type": trace.get("resource_type"),
                })
        return errors


class MDSOError(BaseModel):
    """Categorized MDSO error"""
    circuit_id: str
    resource_id: str
    error_text: str
    error_code: Optional[str] = None
    defect_number: Optional[str] = None
    timestamp: datetime
    device_tid: Optional[str] = None
    management_ip: Optional[str] = None
    resource_type: Optional[str] = None
