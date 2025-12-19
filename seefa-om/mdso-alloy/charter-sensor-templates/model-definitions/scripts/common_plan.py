"""
Common Plan Processing Module with OpenTelemetry Instrumentation
Provides plan execution and processing utilities with comprehensive observability
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# OpenTelemetry imports
from opentelemetry import trace, baggage
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
import structlog

# Standard logging
logger = logging.getLogger(__name__)

# Global state for OTEL initialization
_otel_initialized = False
_tracer = None
_otel_logger = None


class NDJSONFileExporter(SpanExporter):
    """
    File exporter that writes spans in NDJSON format (one JSON object per line)
    Writes to /opt/ciena/bp2/alloy-collector/traces.ndjson
    """
    
    def __init__(self, file_path: str = "/opt/ciena/bp2/alloy-collector/traces.ndjson"):
        """
        Initialize NDJSON file exporter
        
        Args:
            file_path: Path to the NDJSON file for writing traces
        """
        self.file_path = Path(file_path)
        self._ensure_directory_exists()
        self._file_handle = None
        
    def _ensure_directory_exists(self):
        """Ensure the directory for traces.ndjson exists"""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {self.file_path.parent}")
        except Exception as e:
            logger.error(f"Failed to create directory {self.file_path.parent}: {e}")
            raise
    
    def _get_file_handle(self):
        """Get or create file handle in append mode"""
        if self._file_handle is None or self._file_handle.closed:
            try:
                self._file_handle = open(self.file_path, 'a', encoding='utf-8')
            except Exception as e:
                logger.error(f"Failed to open file {self.file_path}: {e}")
                raise
        return self._file_handle
    
    def _span_to_ndjson(self, span: Span) -> Dict[str, Any]:
        """
        Convert OpenTelemetry span to NDJSON-compatible dictionary
        
        Args:
            span: OpenTelemetry span to convert
            
        Returns:
            Dictionary representation of the span in OTLP-like format
        """
        span_context = span.get_span_context()
        
        # Get parent span ID if available
        parent_span_id = None
        try:
            # Try to get parent from span's parent context
            if hasattr(span, 'parent') and span.parent:
                if hasattr(span.parent, 'span_id') and span.parent.span_id:
                    parent_span_id = format(span.parent.span_id, "016x")
        except (AttributeError, TypeError):
            # Parent not available - this is normal for root spans
            pass
        
        # Build span data structure
        span_data = {
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
            "parent_span_id": parent_span_id,
            "name": span.name,
            "kind": span.kind.name if hasattr(span.kind, 'name') else str(span.kind),
            "start_time_unix_nano": span.start_time,
            "end_time_unix_nano": span.end_time if span.end_time else None,
            "attributes": dict(span.attributes) if span.attributes else {},
            "events": [
                {
                    "name": event.name,
                    "time_unix_nano": event.timestamp,
                    "attributes": dict(event.attributes) if event.attributes else {}
                }
                for event in span.events
            ] if span.events else [],
            "status": {
                "code": span.status.status_code.name if hasattr(span.status.status_code, 'name') else str(span.status.status_code),
                "message": span.status.description if span.status.description else None
            } if span.status else None,
            "resource": {
                "attributes": dict(span.resource.attributes) if span.resource and span.resource.attributes else {}
            } if span.resource else {}
        }
        
        return span_data
    
    def export(self, spans: List[Span]) -> SpanExportResult:
        """
        Export spans to NDJSON file (one span per line)
        
        Args:
            spans: List of spans to export
            
        Returns:
            SpanExportResult indicating success or failure
        """
        if not spans:
            return SpanExportResult.SUCCESS
        
        try:
            file_handle = self._get_file_handle()
            
            for span in spans:
                if span.is_recording():
                    span_data = self._span_to_ndjson(span)
                    # Write as single line JSON
                    json_line = json.dumps(span_data, default=str)
                    file_handle.write(json_line + '\n')
            
            # Flush to ensure data is written
            file_handle.flush()
            
            return SpanExportResult.SUCCESS
            
        except Exception as e:
            logger.error(f"Failed to export spans to {self.file_path}: {e}")
            return SpanExportResult.FAILURE
    
    def shutdown(self):
        """Shutdown the exporter and close file handle"""
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.close()
                logger.info(f"Closed NDJSON file exporter: {self.file_path}")
            except Exception as e:
                logger.error(f"Error closing file {self.file_path}: {e}")
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any pending spans"""
        try:
            if self._file_handle and not self._file_handle.closed:
                self._file_handle.flush()
            return True
        except Exception as e:
            logger.error(f"Error flushing file {self.file_path}: {e}")
            return False


class CommonPlan:
    """
    Common plan processing class with OpenTelemetry instrumentation
    """
    
    def __init__(self, plan_name: Optional[str] = None, **kwargs):
        """
        Initialize CommonPlan instance
        
        Args:
            plan_name: Name of the plan being executed
            **kwargs: Additional plan configuration
        """
        self.plan_name = plan_name or "unknown_plan"
        self.config = kwargs
        self._setup_otel_once()
    
    def _setup_otel_once(self):
        """Setup OpenTelemetry instrumentation (only once globally)"""
        global _otel_initialized, _tracer, _otel_logger
        
        if _otel_initialized:
            return
        
        try:
            # Get configuration from environment or defaults
            service_name = os.getenv("OTEL_SERVICE_NAME", "mdso-scriptplan")
            service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
            environment = os.getenv("DEPLOYMENT_ENV", os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", "dev"))
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://159.56.4.94:55681")
            
            # Create resource with service metadata
            resource = Resource.create({
                SERVICE_NAME: service_name,
                SERVICE_VERSION: service_version,
                DEPLOYMENT_ENVIRONMENT: environment,
                "telemetry.sdk.name": "opentelemetry",
                "telemetry.sdk.language": "python",
                "telemetry.sdk.version": "1.20.0",
            })
            
            # Create tracer provider
            provider = TracerProvider(resource=resource)
            
            # Configure OTLP HTTP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=f"{otlp_endpoint}/v1/traces",
                timeout=30,
            )
            
            # Configure NDJSON file exporter
            ndjson_exporter = NDJSONFileExporter()
            
            # Add batch span processors for both exporters
            otlp_processor = BatchSpanProcessor(
                otlp_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,
            )
            
            file_processor = BatchSpanProcessor(
                ndjson_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,
            )
            
            provider.add_span_processor(otlp_processor)
            provider.add_span_processor(file_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(provider)
            
            # Get tracer
            _tracer = trace.get_tracer(__name__, version=service_version)
            
            # Setup structured logging
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.PrintLoggerFactory(),
                wrapper_class=structlog.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            # Create logger with trace context processor
            def add_trace_context(logger, method_name, event_dict):
                """Add trace_id and span_id to logs"""
                span = trace.get_current_span()
                if span and span.get_span_context().is_valid:
                    ctx = span.get_span_context()
                    event_dict["trace_id"] = format(ctx.trace_id, "032x")
                    event_dict["span_id"] = format(ctx.span_id, "016x")
                return event_dict
            
            # Configure structlog with trace context
            current_config = structlog.get_config()
            processors = list(current_config.get("processors", []))
            
            # Insert trace context processor
            insert_index = 1
            for i, proc in enumerate(processors):
                if hasattr(proc, '__name__') and 'merge_contextvars' in proc.__name__:
                    insert_index = i + 1
                    break
            
            if add_trace_context not in processors:
                processors.insert(insert_index, add_trace_context)
                structlog.configure(
                    processors=processors,
                    logger_factory=current_config.get("logger_factory"),
                    wrapper_class=current_config.get("wrapper_class"),
                    cache_logger_on_first_use=current_config.get("cache_logger_on_first_use", True),
                )
            
            _otel_logger = structlog.get_logger(service_name)
            
            _otel_initialized = True
            
            logger.info(
                f"OTel initialized: service={service_name}, endpoint={otlp_endpoint}, "
                f"env={environment}, file_exporter={ndjson_exporter.file_path}"
            )
            _otel_logger.info(
                "OpenTelemetry initialized",
                service=service_name,
                version=service_version,
                environment=environment,
                otlp_endpoint=otlp_endpoint,
                ndjson_file=str(ndjson_exporter.file_path)
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}", exc_info=True)
            # Don't raise - allow plan execution to continue without OTEL
    
    def run(self):
        """
        Main execution method for plan processing
        This method is called at line 434 in tracebacks
        """
        global _tracer, _otel_logger
        
        # Ensure OTEL is initialized
        self._setup_otel_once()
        
        # Get tracer and logger
        tracer = _tracer or trace.get_tracer(__name__)
        otel_logger = _otel_logger or structlog.get_logger("mdso-scriptplan")
        
        # Extract correlation context from config
        circuit_id = self.config.get("circuit_id")
        resource_id = self.config.get("resource_id")
        product_id = self.config.get("product_id")
        plan_name = self.plan_name
        
        # Create main span for plan execution
        with tracer.start_as_current_span(
            f"plan.execute.{plan_name}",
            kind=SpanKind.INTERNAL
        ) as span:
            # Set span attributes
            span.set_attribute("plan.name", plan_name)
            if circuit_id:
                span.set_attribute("circuit_id", str(circuit_id))
            if resource_id:
                span.set_attribute("resource_id", str(resource_id))
            if product_id:
                span.set_attribute("product_id", str(product_id))
            span.set_attribute("mdso.component", "scriptplan")
            
            # Inject correlation context
            if circuit_id:
                baggage.set_baggage("circuit_id", str(circuit_id))
            if resource_id:
                baggage.set_baggage("resource_id", str(resource_id))
            if product_id:
                baggage.set_baggage("product_id", str(product_id))
            
            # Log plan execution started
            span.add_event("plan.execution.started", {
                "plan_name": plan_name,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            otel_logger.info(
                "Plan execution started",
                plan_name=plan_name,
                circuit_id=circuit_id,
                resource_id=resource_id,
                product_id=product_id,
                state="STARTED"
            )
            
            try:
                # Execute the plan processing
                response = self.process()
                
                # Log plan execution completed
                span.add_event("plan.execution.completed", {
                    "plan_name": plan_name,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("plan.success", True)
                
                otel_logger.info(
                    "Plan execution completed",
                    plan_name=plan_name,
                    circuit_id=circuit_id,
                    resource_id=resource_id,
                    product_id=product_id,
                    state="COMPLETED"
                )
                
                return response
                
            except Exception as e:
                # Log plan execution failed
                error_msg = str(e)
                span.add_event("plan.execution.failed", {
                    "plan_name": plan_name,
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                
                span.set_status(Status(StatusCode.ERROR, error_msg))
                span.record_exception(e)
                span.set_attribute("plan.success", False)
                span.set_attribute("plan.error", error_msg)
                
                otel_logger.error(
                    "Plan execution failed",
                    plan_name=plan_name,
                    circuit_id=circuit_id,
                    resource_id=resource_id,
                    product_id=product_id,
                    error=error_msg,
                    state="FAILED",
                    exc_info=True
                )
                
                raise
    
    def process(self):
        """
        Process the plan - to be implemented by subclasses or overridden
        This is called from the run method
        """
        # Default implementation - override in subclasses
        logger.info(f"Processing plan: {self.plan_name}")
        return {"status": "processed", "plan_name": self.plan_name}


# Convenience function for standalone usage
def run(plan_name: Optional[str] = None, **kwargs):
    """
    Convenience function to execute a plan
    
    Args:
        plan_name: Name of the plan
        **kwargs: Plan configuration and correlation context
        
    Returns:
        Result from plan execution
    """
    plan = CommonPlan(plan_name=plan_name, **kwargs)
    return plan.run()

