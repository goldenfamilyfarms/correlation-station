"""
OpenTelemetry Configuration Loader
Reads standard OTEL environment variables and provides unified configuration
"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class OTelConfig:
    """OpenTelemetry configuration from environment variables"""
    
    def __init__(self):
        # Service identification
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        
        # Resource attributes
        resource_attrs_str = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
        self.resource_attributes = self._parse_resource_attributes(resource_attrs_str)
        
        # Environment
        self.deployment_environment = (
            self.resource_attributes.get("deployment.environment") or
            os.getenv("OTEL_DEPLOYMENT_ENV") or
            os.getenv("DEPLOYMENT_ENV") or
            os.getenv("ENVIRONMENT", "production")
        )
        
        # Exporters
        self.traces_exporter = os.getenv("OTEL_TRACES_EXPORTER", "otlp")
        self.metrics_exporter = os.getenv("OTEL_METRICS_EXPORTER", "otlp")
        
        # OTLP Configuration (for Datadog Agent)
        self.otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        self.otlp_protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
        self.otlp_headers = self._parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
        
        # Propagation
        propagators_str = os.getenv("OTEL_PROPAGATORS", "tracecontext,baggage")
        self.propagators = [p.strip() for p in propagators_str.split(",") if p.strip()]
        
        # Sampling
        self.traces_sampler = os.getenv("OTEL_TRACES_SAMPLER", "parentbased_traceidratio")
        self.traces_sampler_arg = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))
        
        # Correlation Engine (for dual export)
        self.correlation_engine_url = os.getenv(
            "CORRELATION_ENGINE_URL",
            os.getenv("CORRELATION_GATEWAY_URL", "http://159.56.4.94:8080")
        )
        
        # Log correlation
        self.log_correlation = os.getenv("OTEL_PYTHON_LOG_CORRELATION", "false").lower() == "true"
        
        # Validate required settings
        self._validate()
    
    def _parse_resource_attributes(self, attrs_str: str) -> Dict[str, str]:
        """Parse OTEL_RESOURCE_ATTRIBUTES string into dict"""
        attrs = {}
        if not attrs_str:
            return attrs
        
        for pair in attrs_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                attrs[key.strip()] = value.strip()
        
        return attrs
    
    def _parse_headers(self, headers_str: str) -> Dict[str, str]:
        """Parse OTEL_EXPORTER_OTLP_HEADERS string into dict"""
        headers = {}
        if not headers_str:
            return headers
        
        for pair in headers_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                headers[key.strip()] = value.strip()
        
        return headers
    
    def _validate(self):
        """Validate configuration"""
        if not self.service_name:
            logger.warning("OTEL_SERVICE_NAME not set - using fallback")
        
        if not self.otlp_endpoint:
            logger.warning(
                "OTEL_EXPORTER_OTLP_ENDPOINT not set - Datadog Agent export will be disabled. "
                "Set to Datadog Agent OTLP endpoint (e.g., http://localhost:4318)"
            )
        
        # Validate protocol
        valid_protocols = ["http/protobuf", "grpc", "http/json"]
        if self.otlp_protocol not in valid_protocols:
            logger.warning(
                f"OTEL_EXPORTER_OTLP_PROTOCOL={self.otlp_protocol} not recognized. "
                f"Valid values: {valid_protocols}. Defaulting to http/protobuf"
            )
            self.otlp_protocol = "http/protobuf"
    
    def get_datadog_traces_endpoint(self) -> Optional[str]:
        """Get Datadog Agent traces endpoint"""
        if not self.otlp_endpoint:
            return None
        
        # OTLP endpoint should be base URL, append signal path
        if self.otlp_protocol == "grpc":
            # gRPC uses different port typically, but endpoint should be full URL
            return self.otlp_endpoint if ":4317" in self.otlp_endpoint else self.otlp_endpoint.replace(":4318", ":4317")
        else:
            # HTTP/protobuf uses /v1/traces
            base = self.otlp_endpoint.rstrip("/")
            if "/v1/traces" not in base:
                return f"{base}/v1/traces"
            return base
    
    def get_datadog_metrics_endpoint(self) -> Optional[str]:
        """Get Datadog Agent metrics endpoint"""
        if not self.otlp_endpoint:
            return None
        
        if self.otlp_protocol == "grpc":
            return self.otlp_endpoint if ":4317" in self.otlp_endpoint else self.otlp_endpoint.replace(":4318", ":4317")
        else:
            base = self.otlp_endpoint.rstrip("/")
            if "/v1/metrics" not in base:
                return f"{base}/v1/metrics"
            return base
    
    def get_correlation_traces_endpoint(self) -> str:
        """Get correlation engine traces endpoint"""
        base = self.correlation_engine_url.rstrip("/")
        return f"{base}/api/otlp/v1/traces"
    
    def get_correlation_metrics_endpoint(self) -> str:
        """Get correlation engine metrics endpoint"""
        base = self.correlation_engine_url.rstrip("/")
        return f"{base}/api/otlp/v1/metrics"
    
    def is_dual_export_enabled(self) -> bool:
        """Check if dual export is enabled (both Datadog Agent and correlation engine)"""
        return bool(self.otlp_endpoint) and bool(self.correlation_engine_url)
    
    def __repr__(self) -> str:
        return (
            f"OTelConfig(service={self.service_name}, "
            f"version={self.service_version}, "
            f"env={self.deployment_environment}, "
            f"otlp_endpoint={self.otlp_endpoint}, "
            f"protocol={self.otlp_protocol})"
        )
