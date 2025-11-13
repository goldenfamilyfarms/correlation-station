"""
common_otel.py - OpenTelemetry-enabled CommonPlan replacement

Drop-in replacement for common_plan.py logging with OTel SDK instrumentation.
Maintains BP's enter_exit_log() API while emitting OTel spans + logs.

Author: Derrick Golden
Version: 1.0.0
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler

# OpenTelemetry imports
from opentelemetry import trace, baggage
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.trace import SpanAttributes
import structlog

# Import base Plan class
import sys
sys.path.append("model-definitions")
from scripts.scriptplan import Plan


class OTelPlan(Plan):
    """
    OpenTelemetry-instrumented Plan class

    Drop-in replacement for CommonPlan that:
    1. Replaces splunk_logger_setup() with otel_logger_setup()
    2. Enhances enter_exit_log() to emit OTel spans + structured logs
    3. Maintains backward compatibility with existing BP products

    Usage:
        from otel_instrumentation.common_otel import OTelPlan

        class MyProduct(OTelPlan):
            def process(self):
                self.enter_exit_log("Starting my process")
                # ... your code ...
                self.enter_exit_log("Completed my process", "COMPLETED")
    """

    # OpenTelemetry configuration from environment
    OTEL_EXPORTER_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://159.56.4.94:55681")
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "mdso-scriptplan")
    OTEL_DEPLOYMENT_ENV = os.getenv("OTEL_DEPLOYMENT_ENV", "dev")

    # Enable/disable OTel (can be toggled via env var)
    OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"

    # Class-level tracer
    _tracer: Optional[trace.Tracer] = None
    _tracer_provider: Optional[TracerProvider] = None

    def __init__(self, *args, **kwargs):
        """Initialize OTel-enabled Plan"""
        super().__init__(*args, **kwargs)

        # Initialize OTel if enabled
        if self.OTEL_ENABLED and self._tracer is None:
            self._init_otel()

        # Replace splunk_logger with otel_logger
        self.otel_logger = self.otel_logger_setup()

        # Keep backward compatibility
        self.splunk_logger = self.otel_logger

        # Track current span
        self._current_span: Optional[trace.Span] = None
        self._workflow_span: Optional[trace.Span] = None

    @classmethod
    def _init_otel(cls):
        """Initialize OpenTelemetry tracer (class-level, once)"""
        if cls._tracer is not None:
            return

        # Create resource with service metadata
        resource = Resource.create({
            "service.name": cls.OTEL_SERVICE_NAME,
            "service.version": os.getenv("MDSO_VERSION", "24.08"),
            "deployment.environment": cls.OTEL_DEPLOYMENT_ENV,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "1.20.0",
        })

        # Create tracer provider
        cls._tracer_provider = TracerProvider(resource=resource)

        # Configure OTLP exporter (HTTP to OTel Gateway)
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{cls.OTEL_EXPORTER_ENDPOINT}/v1/traces",
            timeout=30,  # 30 seconds timeout
        )

        # Add batch span processor for performance
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,  # Export every 5 seconds
        )
        cls._tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(cls._tracer_provider)

        # Get tracer instance
        cls._tracer = trace.get_tracer(__name__, version="1.0.0")

        logging.info(f"OpenTelemetry initialized: exporter={cls.OTEL_EXPORTER_ENDPOINT}, service={cls.OTEL_SERVICE_NAME}")

    def otel_logger_setup(self):
        """
        Setup OTel-compatible logger (replaces splunk_logger_setup)

        Creates structured logger that outputs to:
        1. File: /bp2/log/splunk-logs/sensor-templates-otel.log (for backward compat)
        2. StdOut: Structured JSON logs (picked up by Alloy agent)

        Returns:
            structlog.BoundLogger: Structured logger instance
        """
        # Configure structlog for structured logging
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

        # Create bound logger with context
        logger = structlog.get_logger("OTelSensorLogger")
        logger = logger.bind(
            service=self.OTEL_SERVICE_NAME,
            resource_id=self.resource_id if hasattr(self, 'resource_id') else None,
            resource_type_id=self.resource.get("resourceTypeId") if hasattr(self, 'resource') else None,
        )

        # Also setup file handler for backward compatibility
        if not os.path.exists("/bp2/log/splunk-logs"):
            os.makedirs("/bp2/log/splunk-logs")

        file_logger = logging.getLogger("SensorOTelFileLogger")
        file_logger.setLevel(logging.DEBUG)
        file_handler = RotatingFileHandler(
            "/bp2/log/splunk-logs/sensor-templates-otel.log",
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        file_logger.addHandler(file_handler)

        self._file_logger = file_logger

        return logger

    def enter_exit_log(self, message: str, state: str = "STARTED"):
        """
        Enhanced enter_exit_log with OTel span emission

        Drop-in replacement for BP's enter_exit_log() that:
        1. Maintains original BP orchestration_trace behavior
        2. Emits OTel spans for distributed tracing
        3. Emits structured logs
        4. Propagates trace context via baggage

        Args:
            message: Log message
            state: Process state (STARTED, COMPLETED, FAILED)
        """
        if not hasattr(self, 'EnableEnterExitLog') or self.EnableEnterExitLog is False:
            return

        # Call original BP behavior (writes to TraceLog resource)
        super().enter_exit_log(message, state)

        # Emit OTel signals
        if self.OTEL_ENABLED:
            self._emit_otel_span(message, state)
            self._emit_structured_log(message, state)

    def _emit_otel_span(self, message: str, state: str):
        """Emit OpenTelemetry span for this process step"""
        if self._tracer is None:
            return

        # Extract correlation keys
        trace_id = self.params.get("traceId", "unknown")
        resource_id = self.resource_id if hasattr(self, 'resource_id') else "unknown"
        circuit_id = self.properties.get("circuit_id") if hasattr(self, 'properties') else None
        product_id = self.resource.get("productId") if hasattr(self, 'resource') else None
        resource_type_id = self.resource.get("resourceTypeId") if hasattr(self, 'resource') else "unknown"

        # Determine span operation
        if state == "STARTED":
            # Start new span
            span_name = f"mdso.product.{self.the_class if hasattr(self, 'the_class') else 'process'}"

            self._current_span = self._tracer.start_span(
                name=span_name,
                kind=trace.SpanKind.INTERNAL,
                attributes={
                    # Standard attributes
                    SpanAttributes.CODE_FUNCTION: self.the_class if hasattr(self, 'the_class') else "unknown",
                    SpanAttributes.CODE_NAMESPACE: "mdso.scriptplan",

                    # MDSO-specific attributes
                    "mdso.resource_id": resource_id,
                    "mdso.resource_type_id": resource_type_id,
                    "mdso.trace_id": trace_id,
                    "mdso.operation": self.params.get("operation", "unknown"),
                    "mdso.scriptplan.process": self.the_class if hasattr(self, 'the_class') else "unknown",

                    # Correlation keys
                    "circuit_id": circuit_id,
                    "product_id": product_id,
                    "resource_type": resource_type_id.split(".")[-1] if resource_type_id else "unknown",
                }
            )

            # Set baggage for context propagation
            ctx = baggage.set_baggage("circuit_id", circuit_id)
            ctx = baggage.set_baggage("product_id", product_id, context=ctx)
            ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

            # Add span event
            self._current_span.add_event(
                name="process.started",
                attributes={
                    "message": message,
                    "state": state,
                }
            )

        elif state in ["COMPLETED", "FAILED"]:
            # End current span
            if self._current_span is not None:
                # Add completion event
                self._current_span.add_event(
                    name=f"process.{state.lower()}",
                    attributes={
                        "message": message,
                        "state": state,
                        "elapsed_time": int(time.time() - self.common_plan_start_time) if hasattr(self, 'common_plan_start_time') else 0,
                    }
                )

                # Set span status
                if state == "FAILED":
                    self._current_span.set_status(
                        Status(StatusCode.ERROR, message)
                    )
                    if hasattr(self, 'categorized_error'):
                        self._current_span.set_attribute("categorized_error", self.categorized_error)
                else:
                    self._current_span.set_status(Status(StatusCode.OK))

                # End span
                self._current_span.end()
                self._current_span = None

        else:
            # Intermediate state - add event to current span
            if self._current_span is not None:
                self._current_span.add_event(
                    name="process.progress",
                    attributes={
                        "message": message,
                        "state": state,
                    }
                )

    def _emit_structured_log(self, message: str, state: str):
        """Emit structured log entry"""
        # Extract context
        trace_id = self.params.get("traceId", "unknown")
        resource_id = self.resource_id if hasattr(self, 'resource_id') else "unknown"
        circuit_id = self.properties.get("circuit_id") if hasattr(self, 'properties') else None
        product_id = self.resource.get("productId") if hasattr(self, 'resource') else None
        resource_type_id = self.resource.get("resourceTypeId") if hasattr(self, 'resource') else "unknown"

        # Determine log level
        if state == "FAILED":
            log_level = "error"
        elif state == "COMPLETED":
            log_level = "info"
        else:
            log_level = "debug"

        # Build structured log entry
        log_entry = {
            "message": message,
            "state": state,
            "trace_id": trace_id,
            "resource_id": resource_id,
            "circuit_id": circuit_id,
            "product_id": product_id,
            "resource_type_id": resource_type_id,
            "process": self.the_class if hasattr(self, 'the_class') else "unknown",
            "elapsed_time": int(time.time() - self.common_plan_start_time) if hasattr(self, 'common_plan_start_time') else 0,
        }

        # Add error context if failed
        if state == "FAILED" and hasattr(self, 'categorized_error'):
            log_entry["categorized_error"] = self.categorized_error

        # Emit to structured logger
        getattr(self.otel_logger, log_level)(
            message,
            **log_entry
        )

        # Also emit to file logger for backward compat
        self._file_logger.log(
            logging.ERROR if state == "FAILED" else logging.INFO,
            f"{state} - {message} | trace_id={trace_id} | resource_id={resource_id} | circuit_id={circuit_id}"
        )

    def start_workflow_span(self):
        """
        Start a parent span for the entire workflow

        Call this at the beginning of your process() method to create
        a parent span that encompasses all child process steps.
        """
        if not self.OTEL_ENABLED or self._tracer is None:
            return

        resource_id = self.resource_id if hasattr(self, 'resource_id') else "unknown"
        circuit_id = self.properties.get("circuit_id") if hasattr(self, 'properties') else None
        product_id = self.resource.get("productId") if hasattr(self, 'resource') else None
        resource_type_id = self.resource.get("resourceTypeId") if hasattr(self, 'resource') else "unknown"
        operation = self.params.get("operation", "unknown")

        span_name = f"mdso.workflow.{resource_type_id.split('.')[-1] if resource_type_id else 'unknown'}"

        self._workflow_span = self._tracer.start_span(
            name=span_name,
            kind=trace.SpanKind.INTERNAL,
            attributes={
                "mdso.resource_id": resource_id,
                "mdso.resource_type_id": resource_type_id,
                "mdso.operation": operation,
                "circuit_id": circuit_id,
                "product_id": product_id,
                "workflow.type": "mdso_scriptplan",
            }
        )

    def end_workflow_span(self, success: bool = True):
        """
        End the workflow span

        Call this at the end of your process() method.

        Args:
            success: Whether workflow completed successfully
        """
        if self._workflow_span is not None:
            if success:
                self._workflow_span.set_status(Status(StatusCode.OK))
            else:
                self._workflow_span.set_status(Status(StatusCode.ERROR))

            self._workflow_span.end()
            self._workflow_span = None

    @classmethod
    def shutdown_otel(cls):
        """Shutdown OTel tracer provider (call on exit)"""
        if cls._tracer_provider is not None:
            cls._tracer_provider.shutdown()
            cls._tracer_provider = None
            cls._tracer = None
