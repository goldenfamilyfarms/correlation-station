"""Data models for the correlation engine"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    """Individual log record from OTLP"""
    timestamp: str
    severity: str = "INFO"
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    circuit_id: Optional[str] = None
    product_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type_id: Optional[str] = None
    request_id: Optional[str] = None
    labels: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ResourceInfo(BaseModel):
    """Resource information for log batch"""
    service: str
    host: str
    env: str


class LogBatch(BaseModel):
    """Batch of logs from Gateway/Alloy"""
    resource: ResourceInfo
    records: List[LogRecord]


class OTLPLogsRequest(BaseModel):
    """OTLP logs request format"""
    resourceLogs: List[Dict[str, Any]]


class OTLPTracesRequest(BaseModel):
    """OTLP traces request format"""
    resourceSpans: List[Dict[str, Any]]


class OTLPMetricsRequest(BaseModel):
    """OTLP metrics request format"""
    resourceMetrics: List[Dict[str, Any]]


class Correlation(BaseModel):
    """Discovered correlation"""
    correlation_id: str
    trace_id: Optional[str] = None
    service: str
    env: str
    timestamp: datetime
    duration_seconds: float
    log_count: int = 0
    span_count: int = 0
    metrics_count: int = 0
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    participating_services: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)

    # Custom Sense/MDSO attributes
    circuit_id: Optional[str] = None
    product_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type_id: Optional[str] = None
    request_id: Optional[str] = None


class CorrelationQuery(BaseModel):
    """Query for correlations"""
    trace_id: Optional[str] = None
    service: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)


class HealthStatus(BaseModel):
    """Health check response"""
    status: str
    version: str = "1.0.0"
    timestamp: datetime
    components: Dict[str, str]


class HealthResponse(BaseModel):
    """Alternative health check response with more details"""
    status: str
    version: str = "1.0.0"
    uptime_seconds: float
    pipeline_status: Dict[str, Any] = Field(default_factory=dict)


class CorrelationEvent(BaseModel):
    """Correlation event from windowed correlation"""
    correlation_id: str
    trace_id: str
    timestamp: datetime
    service: str
    env: str
    log_count: int = 0
    span_count: int = 0
    circuit_id: Optional[str] = None
    product_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyntheticEvent(BaseModel):
    """Manually injected synthetic correlation event"""
    trace_id: str
    service: str
    message: str
    severity: str = "INFO"
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)