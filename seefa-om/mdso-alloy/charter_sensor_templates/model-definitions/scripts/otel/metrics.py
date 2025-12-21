"""
OTel Metrics and Counters Module
Provides metrics collection for MDSO operations

Author: Derrick Golden
Version: 1.0.0
"""

import logging
import os
from typing import Optional, Dict, Any

# Setup logger first before imports
logger = logging.getLogger(__name__)
logger.info("metrics.py: Starting module import")

# Try importing OpenTelemetry - gracefully degrade if not available
try:
    logger.info("metrics.py: Attempting to import OpenTelemetry metrics modules")
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
    logger.info("metrics.py: Successfully imported OpenTelemetry metrics modules - OTEL_AVAILABLE=True")
except ImportError as e:
    OTEL_AVAILABLE = False
    metrics = MeterProvider = PeriodicExportingMetricReader = None
    OTLPMetricExporter = Resource = None
    logger.warning(f"metrics.py: Failed to import OpenTelemetry metrics modules - OTEL_AVAILABLE=False - Error: {e}")

logger.info(f"metrics.py: Module import complete - OTEL_AVAILABLE={OTEL_AVAILABLE}")

# Global meter provider
_meter_provider = None
_meter = None


def setup_metrics(
    service_name: str = "mdso-scriptplan",
    endpoint: str = None,
    environment: str = "dev",
    version: str = "1.0.0",
    instance: Optional[Any] = None
) -> "metrics.Meter":
    """
    Setup OpenTelemetry metrics for MDSO scriptplan
    
    Args:
        service_name: Service name for resource attributes
        endpoint: OTLP exporter endpoint
        environment: Deployment environment (dev/staging/prod)
        version: Service version
        instance: Optional CommonPlan instance to get constants from
    
    Returns:
        Configured meter instance
    
    Example:
        >>> meter = setup_metrics("mdso-scriptplan", environment="dev")
        >>> counter = meter.create_counter("operation.count")
        >>> counter.add(1, {"operation": "provision"})
    """
    global _meter_provider, _meter
    
    if _meter_provider is not None:
        return _meter
    
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": version,
        "deployment.environment": environment,
    })
    
    # Determine export endpoint from CommonPlan constant or environment variable
    # First try metrics-specific endpoint, then fall back to general OTLP endpoint
    metrics_endpoint = None
    if instance is not None:
        if hasattr(instance, 'OTEL_EXPORTER_OTLP_METRICS_ENDPOINT'):
            metrics_endpoint = getattr(instance, 'OTEL_EXPORTER_OTLP_METRICS_ENDPOINT')
        elif hasattr(instance.__class__, 'OTEL_EXPORTER_OTLP_METRICS_ENDPOINT'):
            metrics_endpoint = getattr(instance.__class__, 'OTEL_EXPORTER_OTLP_METRICS_ENDPOINT')
    
    if metrics_endpoint is None:
        metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", None)
    
    # If no metrics-specific endpoint, try general OTLP endpoint
    if metrics_endpoint is None:
        if instance is not None:
            if hasattr(instance, 'OTEL_EXPORTER_OTLP_ENDPOINT'):
                metrics_endpoint = getattr(instance, 'OTEL_EXPORTER_OTLP_ENDPOINT')
            elif hasattr(instance.__class__, 'OTEL_EXPORTER_OTLP_ENDPOINT'):
                metrics_endpoint = getattr(instance.__class__, 'OTEL_EXPORTER_OTLP_ENDPOINT')
        
        if metrics_endpoint is None:
            metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    
    # Final fallback
    endpoint = endpoint or metrics_endpoint or "http://localhost:4318"  # Alloy OTLP HTTP receiver
    
    # Create metric exporter
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{endpoint}/v1/metrics",
        timeout=30,
    )
    
    # Create metric reader
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=60000,  # Export every 60 seconds
    )
    
    # Create meter provider
    _meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    
    # Set global meter provider
    metrics.set_meter_provider(_meter_provider)
    
    # Create meter
    _meter = metrics.get_meter(__name__)
    
    logger.info(f"Metrics initialized: service={service_name}, endpoint={endpoint}, env={environment}")
    
    return _meter


def get_meter() -> Optional["metrics.Meter"]:
    """
    Get the global meter instance
    
    Returns:
        Meter instance or None if not initialized
    """
    global _meter
    if _meter is None:
        # Try to initialize with defaults
        try:
            _meter = setup_metrics()
        except Exception as e:
            logger.warning(f"Failed to initialize metrics: {e}")
            return None
    return _meter


class MDSOMetrics:
    """
    Helper class for MDSO-specific metrics
    """
    
    def __init__(self, service_name: str = "mdso-scriptplan"):
        self.service_name = service_name
        self.meter = get_meter()
        
        if self.meter is None:
            logger.warning("Metrics not available - meter not initialized")
            return
        
        # Operation counters
        self.operation_counter = self.meter.create_counter(
            "mdso.operation.count",
            description="Total number of operations",
            unit="1"
        )
        
        self.operation_duration = self.meter.create_histogram(
            "mdso.operation.duration",
            description="Duration of operations in milliseconds",
            unit="ms"
        )
        
        # Error counters
        self.error_counter = self.meter.create_counter(
            "mdso.error.count",
            description="Total number of errors",
            unit="1"
        )
        
        # Topology metrics
        self.topology_fetch_counter = self.meter.create_counter(
            "mdso.topology.fetch.count",
            description="Number of topology fetches",
            unit="1"
        )
        
        self.topology_fetch_duration = self.meter.create_histogram(
            "mdso.topology.fetch.duration",
            description="Duration of topology fetches in milliseconds",
            unit="ms"
        )
        
        # Network function metrics
        self.network_function_operation_counter = self.meter.create_counter(
            "mdso.network_function.operation.count",
            description="Number of network function operations",
            unit="1"
        )
        
        self.network_function_operation_duration = self.meter.create_histogram(
            "mdso.network_function.operation.duration",
            description="Duration of network function operations in milliseconds",
            unit="ms"
        )
        
        # Device onboarding metrics
        self.device_onboard_counter = self.meter.create_counter(
            "mdso.device.onboard.count",
            description="Number of devices onboarded",
            unit="1"
        )
        
        self.device_onboard_duration = self.meter.create_histogram(
            "mdso.device.onboard.duration",
            description="Duration of device onboarding in milliseconds",
            unit="ms"
        )
        
        # Provisioning metrics
        self.provisioning_counter = self.meter.create_counter(
            "mdso.provisioning.count",
            description="Number of provisioning operations",
            unit="1"
        )
        
        self.provisioning_duration = self.meter.create_histogram(
            "mdso.provisioning.duration",
            description="Duration of provisioning operations in milliseconds",
            unit="ms"
        )
        
        # Service type counters
        self.service_type_counter = self.meter.create_counter(
            "mdso.service_type.count",
            description="Number of operations by service type",
            unit="1"
        )
        
        # Vendor counters
        self.vendor_counter = self.meter.create_counter(
            "mdso.vendor.operation.count",
            description="Number of operations by vendor",
            unit="1"
        )
    
    def record_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Record an operation
        
        Args:
            operation_name: Name of the operation
            attributes: Additional attributes
        """
        if self.meter is None:
            return
        
        attrs = {"operation": operation_name}
        if attributes:
            attrs.update(attributes)
        
        self.operation_counter.add(1, attrs)
    
    def record_operation_duration(self, operation_name: str, duration_ms: float, attributes: Optional[Dict[str, Any]] = None):
        """
        Record operation duration
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            attributes: Additional attributes
        """
        if self.meter is None:
            return
        
        attrs = {"operation": operation_name}
        if attributes:
            attrs.update(attributes)
        
        self.operation_duration.record(duration_ms, attrs)
    
    def record_error(self, error_category: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Record an error
        
        Args:
            error_category: Error category
            attributes: Additional attributes
        """
        if self.meter is None:
            return
        
        attrs = {"error.category": error_category}
        if attributes:
            attrs.update(attributes)
        
        self.error_counter.add(1, attrs)
    
    def record_topology_fetch(self, circuit_id: str, duration_ms: Optional[float] = None):
        """
        Record a topology fetch
        
        Args:
            circuit_id: Circuit identifier
            duration_ms: Optional duration in milliseconds
        """
        if self.meter is None:
            return
        
        attrs = {"circuit_id": circuit_id}
        self.topology_fetch_counter.add(1, attrs)
        
        if duration_ms is not None:
            self.topology_fetch_duration.record(duration_ms, attrs)
    
    def record_network_function_operation(
        self,
        operation: str,
        tid: Optional[str] = None,
        vendor: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """
        Record a network function operation
        
        Args:
            operation: Operation type (check, query, onboard, etc.)
            tid: Device TID
            vendor: Device vendor
            duration_ms: Optional duration in milliseconds
        """
        if self.meter is None:
            return
        
        attrs = {"operation": operation}
        if tid:
            attrs["network.device.tid"] = tid
        if vendor:
            attrs["network.device.vendor"] = vendor.lower()
        
        self.network_function_operation_counter.add(1, attrs)
        
        if duration_ms is not None:
            self.network_function_operation_duration.record(duration_ms, attrs)
    
    def record_device_onboard(
        self,
        vendor: str,
        duration_ms: Optional[float] = None,
        success: bool = True
    ):
        """
        Record a device onboarding
        
        Args:
            vendor: Device vendor
            duration_ms: Optional duration in milliseconds
            success: Whether onboarding was successful
        """
        if self.meter is None:
            return
        
        attrs = {
            "network.device.vendor": vendor.lower(),
            "success": str(success).lower()
        }
        
        self.device_onboard_counter.add(1, attrs)
        
        if duration_ms is not None:
            self.device_onboard_duration.record(duration_ms, attrs)
    
    def record_provisioning(
        self,
        service_type: str,
        context: str,
        duration_ms: Optional[float] = None,
        device_count: Optional[int] = None
    ):
        """
        Record a provisioning operation
        
        Args:
            service_type: Service type (FIA, ELAN, ELINE, etc.)
            context: Provisioning context (PE, CPE, etc.)
            duration_ms: Optional duration in milliseconds
            device_count: Number of devices provisioned
        """
        if self.meter is None:
            return
        
        attrs = {
            "service_type": service_type,
            "context": context
        }
        if device_count is not None:
            attrs["device_count"] = str(device_count)
        
        self.provisioning_counter.add(1, attrs)
        self.service_type_counter.add(1, {"service_type": service_type})
        
        if duration_ms is not None:
            self.provisioning_duration.record(duration_ms, attrs)
    
    def record_vendor_operation(self, vendor: str, operation: str):
        """
        Record a vendor-specific operation
        
        Args:
            vendor: Device vendor
            operation: Operation type
        """
        if self.meter is None:
            return
        
        attrs = {
            "network.device.vendor": vendor.lower(),
            "operation": operation
        }
        
        self.vendor_counter.add(1, attrs)

