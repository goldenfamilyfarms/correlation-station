"""
OTel Mixin for MDSO Scriptplan Products
Provides non-invasive OpenTelemetry instrumentation

Based on: OTEL_IMPLEMENTATION_STRATEGY.md
"""
import os
import logging
from typing import Optional, Dict, Any, List
# Try importing OpenTelemetry - gracefully degrade if not available
try:
    from opentelemetry import trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None

from otel.instrumentation import (
    setup_otel,
    get_otel_logger,
    inject_correlation_context,
    mdso_span,
    extract_correlation_context,
    create_topology_span,
    create_network_function_span,
    add_topology_attributes,
    add_network_function_attributes,
    add_error_attributes,
    set_correlation_baggage,
    record_span_event,
    extract_vendor_from_node_name,
    extract_fqdn_from_node_name,
    validate_beorn_response
)
from otel.otel_mdso_utils import (
    MDSOSpanHelper,
    ErrorPatternMatcher
)
from otel.feature_flags import (
    is_otel_enabled,
    is_otel_sampling_enabled,
    get_otel_sampling_rate
)
from otel.metrics import MDSOMetrics
import time

logger = logging.getLogger(__name__)


class OTelMixin:
    """
    Mixin class to add OTel instrumentation to existing products.
    
    Products can inherit from both CommonPlan and OTelMixin to get
    OTel capabilities without breaking existing logging.
    
    Example:
        class ServiceMapper(CommonPlan, OTelMixin):
            def run(self):
                self.__init_otel__()
                with self.create_root_span():
                    return super().run()
    """

    def __init_otel__(self):
        """Initialize OTel tracer and structured logger"""
        logger.info(f"OTelMixin.__init_otel__: Starting OTel initialization for {self.__class__.__name__}")
        
        # Check feature flag (pass self to access CommonPlan constants)
        if not is_otel_enabled(self):
            logger.warning(f"OTelMixin.__init_otel__: OTel instrumentation disabled via feature flag for {self.__class__.__name__}")
            self._otel_initialized = False
            return
        
        # Prevent double initialization
        if hasattr(self, '_otel_initialized') and self._otel_initialized:
            logger.debug(f"OTelMixin.__init_otel__: OTel already initialized for {self.__class__.__name__}, skipping")
            return

        # Get product/resource type from class name
        product_type = self.__class__.__name__
        service_name = f"mdso.{product_type.lower()}"
        logger.info(f"OTelMixin.__init_otel__: Product type: {product_type}, Service name: {service_name}")

        # Get environment from instance constant, instance attribute, or env var
        environment = (
            getattr(self.__class__, 'MDSO_ENV', None) or
            getattr(self, 'MDSO_ENV', None) or
            getattr(self, 'environment', None) or
            os.getenv("MDSO_ENV", "dev")
        )
        logger.info(f"OTelMixin.__init_otel__: Environment: {environment}")

        # Check export mode from CommonPlan constant or environment variable
        export_mode = (
            getattr(self.__class__, 'OTEL_EXPORT_MODE', None) or
            os.getenv("OTEL_EXPORT_MODE", "not set")
        )
        logger.info(f"OTelMixin.__init_otel__: OTEL_EXPORT_MODE: {export_mode}")

        # Setup OTel tracer (pass self as instance to access CommonPlan constants)
        logger.info(f"OTelMixin.__init_otel__: Calling setup_otel() for {service_name}")
        self.tracer = setup_otel(
            service_name=service_name,
            environment=environment,
            instance=self  # Pass self to access CommonPlan constants
        )
        
        if self.tracer is None:
            logger.error(f"OTelMixin.__init_otel__: setup_otel() returned None - OTel may not be available")
            self._otel_initialized = False
            return
        
        logger.info(f"OTelMixin.__init_otel__: Tracer created successfully: {self.tracer}")

        # Setup structured logger
        self.otel_logger = get_otel_logger(service_name)
        logger.info(f"OTelMixin.__init_otel__: Structured logger created")

        # Helper for span management
        self.span_helper = MDSOSpanHelper()
        self.error_matcher = ErrorPatternMatcher()
        logger.info(f"OTelMixin.__init_otel__: Span helpers initialized")
        
        # Metrics helper
        self.metrics = MDSOMetrics(service_name=service_name)
        logger.info(f"OTelMixin.__init_otel__: Metrics helper initialized")

        # Mark as initialized
        self._otel_initialized = True

        logger.info(f"OTelMixin.__init_otel__: OTel initialization complete for {product_type} (service={service_name}, env={environment})")

    def create_root_span(self, operation_name: Optional[str] = None):
        """
        Create root span for product execution
        
        Respects feature flags - returns no-op context manager if OTel disabled.
        
        Usage:
            with self.create_root_span():
                return super().run()
        """
        if not hasattr(self, '_otel_initialized') or not self._otel_initialized:
            logger.info(f"OTelMixin.create_root_span: OTel not initialized, calling __init_otel__()")
            self.__init_otel__()
        
        # Return no-op context manager if OTel disabled
        if not getattr(self, '_otel_initialized', False):
            logger.warning(f"OTelMixin.create_root_span: OTel not initialized, returning no-op context manager")
            from contextlib import nullcontext
            return nullcontext()

        product_name = self.__class__.__name__
        span_name = operation_name or f"mdso.product.{product_name}"
        logger.info(f"OTelMixin.create_root_span: Creating root span '{span_name}' for {product_name}")

        # Extract correlation context from instance attributes
        correlation_attrs = {}
        if hasattr(self, 'circuit_id') and self.circuit_id:
            correlation_attrs['circuit_id'] = self.circuit_id
        if hasattr(self, 'resource_id') and self.resource_id:
            correlation_attrs['resource_id'] = self.resource_id
        if hasattr(self, 'product_id') and self.product_id:
            correlation_attrs['product_id'] = self.product_id

        if correlation_attrs:
            logger.info(f"OTelMixin.create_root_span: Injecting correlation context: {correlation_attrs}")
            inject_correlation_context(**correlation_attrs)
        else:
            logger.debug(f"OTelMixin.create_root_span: No correlation context found in instance attributes")

        logger.info(f"OTelMixin.create_root_span: Creating mdso_span with name='{span_name}'")
        span_context = mdso_span(
            name=span_name,
            **correlation_attrs
        )
        logger.info(f"OTelMixin.create_root_span: Root span context created successfully")
        return span_context

    def otel_log(self, message: str, level: str = "info", **context):
        """
        Dual logging: standard logger + structured OTel logger
        
        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
            **context: Additional structured context
        """
        # Standard logging (existing behavior)
        if hasattr(self, 'logger'):
            getattr(self.logger, level)(message)

        # Structured OTel logging (new)
        if hasattr(self, 'otel_logger') and getattr(self, '_otel_initialized', False):
            # Extract correlation context
            correlation = extract_correlation_context()
            
            # Merge with provided context
            log_context = {**correlation, **context}
            
            getattr(self.otel_logger, level)(
                message,
                **log_context
            )

            # Add span event if we have a current span
            span = trace.get_current_span()
            if span and span.is_recording():
                span.add_event(
                    name=f"log.{level}",
                    attributes={
                        "message": message,
                        "log.level": level,
                        **log_context
                    }
                )

    def otel_error_handler(self, error_message: str, exception: Optional[Exception] = None):
        """
        Handle errors with OTel instrumentation
        
        Args:
            error_message: Error message
            exception: Optional exception object
        """
        # Categorize error
        error_category = self.error_matcher.categorize_error(error_message)
        
        # Extract identifiers from error
        identifiers = self.error_matcher.extract_all_identifiers(error_message)
        
        # Get current span
        span = trace.get_current_span()
        if span and span.is_recording():
            # Add error attributes
            self.span_helper.add_error_attributes(
                span=span,
                error_category=error_category.get('category'),
                error_message=error_message,
                is_new_error=True
            )
            
            # Add extracted identifiers
            for key, value in identifiers.items():
                if value:
                    span.set_attribute(f"error.{key}", value)
            
            # Set span status to error
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_message))
        
        # Log error
        self.otel_log(
            f"Error: {error_message}",
            level="error",
            error_category=error_category.get('category'),
            error_type=error_category.get('type'),
            **identifiers
        )
        
        # Standard error logging (existing)
        if hasattr(self, 'logger'):
            self.logger.error(error_message, exc_info=exception)

    def create_topology_span_context(self, circuit_id: str, operation: str = "fetch"):
        """
        Create a context manager for Beorn topology operations
        
        Args:
            circuit_id: Circuit identifier
            operation: Operation type (fetch, parse, validate)
        
        Returns:
            Context manager that creates and manages a topology span
        
        Example:
            >>> with self.create_topology_span_context("123-456", "fetch") as span:
            ...     # ... fetch topology ...
            ...     add_topology_attributes(span, service_type="FIA", vendor="juniper")
        """
        if not getattr(self, '_otel_initialized', False):
            from contextlib import nullcontext
            return nullcontext()
        
        span = self.span_helper.create_topology_span(
            self.tracer,
            circuit_id,
            operation
        )
        
        # Return a context manager
        from contextlib import contextmanager
        
        @contextmanager
        def span_context():
            try:
                yield span
            finally:
                span.end()
        
        return span_context()

    def create_network_function_span_context(
        self,
        tid: str,
        fqdn: Optional[str] = None,
        operation: str = "check"
    ):
        """
        Create a context manager for network function operations
        
        Args:
            tid: Device TID
            fqdn: Device FQDN (optional)
            operation: Operation type (check, query, validate)
        
        Returns:
            Context manager that creates and manages a network function span
        
        Example:
            >>> with self.create_network_function_span_context("TID123", "device.example.com", "check") as span:
            ...     # ... check device ...
            ...     add_network_function_attributes(span, communication_state="reachable", vendor="adva")
        """
        if not getattr(self, '_otel_initialized', False):
            from contextlib import nullcontext
            return nullcontext()
        
        span = self.span_helper.create_network_function_span(
            self.tracer,
            tid,
            fqdn,
            operation
        )
        
        # Return a context manager
        from contextlib import contextmanager
        
        @contextmanager
        def span_context():
            try:
                yield span
            finally:
                span.end()
        
        return span_context()

    def add_topology_attributes_to_span(
        self,
        span: Optional["trace.Span"] = None,
        service_type: Optional[str] = None,
        vendor: Optional[str] = None,
        fqdn: Optional[str] = None,
        topology_node_count: Optional[int] = None,
        validation_status: Optional[bool] = None,
    ):
        """
        Add Beorn topology-specific attributes to current or provided span
        
        Args:
            span: Optional span (uses current span if not provided)
            service_type: Service type (FIA, ELAN, ELINE, etc.)
            vendor: Device vendor (adva, juniper, cisco, rad)
            fqdn: Device FQDN
            topology_node_count: Number of nodes in topology
            validation_status: Whether topology validation passed
        
        Example:
            >>> self.add_topology_attributes_to_span(
            ...     service_type="FIA",
            ...     vendor="juniper",
            ...     topology_node_count=5,
            ...     validation_status=True
            ... )
        """
        if not getattr(self, '_otel_initialized', False):
            return
        
        if span is None:
            span = trace.get_current_span()
        
        if span and span.is_recording():
            self.span_helper.add_topology_attributes(
                span=span,
                service_type=service_type,
                vendor=vendor,
                fqdn=fqdn,
                topology_node_count=topology_node_count,
                validation_status=validation_status
            )

    def add_network_function_attributes_to_span(
        self,
        span: Optional["trace.Span"] = None,
        communication_state: Optional[str] = None,
        ip_address: Optional[str] = None,
        vendor: Optional[str] = None,
        device_role: Optional[str] = None,
        provider_resource_id: Optional[str] = None,
    ):
        """
        Add network function-specific attributes to current or provided span
        
        Args:
            span: Optional span (uses current span if not provided)
            communication_state: Device communication state
            ip_address: Device IP address
            vendor: Device vendor
            device_role: Device role (CPE, PE)
            provider_resource_id: MDSO provider resource ID
        
        Example:
            >>> self.add_network_function_attributes_to_span(
            ...     communication_state="reachable",
            ...     ip_address="10.0.0.1",
            ...     vendor="adva",
            ...     device_role="CPE"
            ... )
        """
        if not getattr(self, '_otel_initialized', False):
            return
        
        if span is None:
            span = trace.get_current_span()
        
        if span and span.is_recording():
            self.span_helper.add_network_function_attributes(
                span=span,
                communication_state=communication_state,
                ip_address=ip_address,
                vendor=vendor,
                device_role=device_role,
                provider_resource_id=provider_resource_id
            )

    def set_correlation_baggage_from_instance(self):
        """
        Set correlation baggage from instance attributes (circuit_id, resource_id, etc.)
        
        Automatically extracts correlation keys from instance and sets them as baggage.
        
        Example:
            >>> # If self.circuit_id, self.fqdn, etc. are set
            >>> self.set_correlation_baggage_from_instance()
        """
        if not getattr(self, '_otel_initialized', False):
            return
        
        # Extract from instance attributes
        circuit_id = getattr(self, 'circuit_id', None)
        resource_id = getattr(self, 'resource_id', None)
        tid = getattr(self, 'tid', None)
        fqdn = getattr(self, 'fqdn', None)
        provider_resource_id = getattr(self, 'provider_resource_id', None)
        
        # Also try to get from resource properties if available
        if not circuit_id and hasattr(self, 'resource'):
            resource = getattr(self, 'resource', {})
            if isinstance(resource, dict):
                props = resource.get('properties', {})
                circuit_id = props.get('circuit_id') or circuit_id
                resource_id = resource.get('id') or resource_id
        
        self.span_helper.set_correlation_baggage(
            circuit_id=circuit_id,
            resource_id=resource_id,
            tid=tid,
            fqdn=fqdn,
            provider_resource_id=provider_resource_id
        )

    def record_span_event_from_instance(
        self,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        span: Optional["trace.Span"] = None
    ):
        """
        Record a span event with attributes, optionally merging instance context
        
        Args:
            event_name: Name of the event
            attributes: Event attributes (will be merged with instance context)
            span: Optional span (uses current span if not provided)
        
        Example:
            >>> self.record_span_event_from_instance(
            ...     "device.provisioning.started",
            ...     {"device_id": "123", "vendor": "juniper"}
            ... )
        """
        if not getattr(self, '_otel_initialized', False):
            return
        
        if span is None:
            span = trace.get_current_span()
        
        if span and span.is_recording():
            # Merge with instance context
            event_attrs = attributes or {}
            
            # Add correlation context if available
            if hasattr(self, 'circuit_id') and self.circuit_id:
                event_attrs.setdefault('circuit_id', self.circuit_id)
            if hasattr(self, 'resource_id') and self.resource_id:
                event_attrs.setdefault('resource_id', self.resource_id)
            
            self.span_helper.record_span_event(span, event_name, event_attrs)

    def extract_and_set_topology_context(self, topology_data: Dict):
        """
        Extract vendor and FQDN from Beorn topology and set correlation baggage
        
        Args:
            topology_data: Beorn topology response data
        
        Example:
            >>> topology = {"node": [{"name": [...]}]}
            >>> self.extract_and_set_topology_context(topology)
        """
        if not getattr(self, '_otel_initialized', False):
            return
        
        from otel.otel_mdso_utils import (
            extract_vendor_from_node_name,
            extract_fqdn_from_node_name
        )
        
        # Extract from topology nodes
        if isinstance(topology_data, dict):
            nodes = topology_data.get('node', [])
            if not nodes and 'data' in topology_data:
                nodes = topology_data.get('data', {}).get('node', [])
            
            for node in nodes:
                node_name = node.get('name', [])
                if isinstance(node_name, list):
                    vendor = extract_vendor_from_node_name(node_name)
                    fqdn = extract_fqdn_from_node_name(node_name)
                    
                    if vendor or fqdn:
                        # Set correlation baggage for this device
                        self.span_helper.set_correlation_baggage(
                            fqdn=fqdn,
                            vendor=vendor
                        )
                        
                        # Also add to current span if available
                        span = trace.get_current_span()
                        if span and span.is_recording():
                            if vendor:
                                span.set_attribute("network.device.vendor", vendor)
                            if fqdn:
                                span.set_attribute("network.device.fqdn", fqdn)

    def timed_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for timing operations and recording metrics
        
        Args:
            operation_name: Name of the operation
            attributes: Additional attributes for metrics
        
        Returns:
            Context manager that records operation duration
        
        Example:
            >>> with self.timed_operation("device.provision", {"vendor": "juniper"}):
            ...     # ... do provisioning ...
        """
        from contextlib import contextmanager
        
        @contextmanager
        def operation_context():
            start_time = time.time()
            try:
                yield
            finally:
                duration_ms = (time.time() - start_time) * 1000
                if getattr(self, '_otel_initialized', False):
                    # Record metrics
                    if hasattr(self, 'metrics'):
                        self.metrics.record_operation(operation_name, attributes)
                        self.metrics.record_operation_duration(operation_name, duration_ms, attributes)
                    
                    # Record span event
                    span = trace.get_current_span()
                    if span and span.is_recording():
                        event_attrs = {
                            "operation": operation_name,
                            "duration_ms": duration_ms
                        }
                        if attributes:
                            event_attrs.update(attributes)
                        span.add_event(f"operation.{operation_name}.completed", attributes=event_attrs)
        
        return operation_context()

    def validate_and_instrument_beorn_response(self, beorn_data: Dict) -> bool:
        """
        Validate Beorn response and add validation status to current span
        
        Args:
            beorn_data: Beorn API response data
        
        Returns:
            True if valid, False otherwise
        
        Example:
            >>> is_valid = self.validate_and_instrument_beorn_response(beorn_response)
            >>> if not is_valid:
            ...     self.otel_log("Invalid Beorn response", level="warning")
        """
        if not getattr(self, '_otel_initialized', False):
            from otel.otel_mdso_utils import validate_beorn_response
            return validate_beorn_response(beorn_data)
        
        is_valid = validate_beorn_response(beorn_data)
        
        # Add validation status to current span
        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute("beorn.response.valid", is_valid)
            span.set_attribute("beorn.response.element_count", len(beorn_data) if isinstance(beorn_data, dict) else 0)
            
            if not is_valid:
                span.set_attribute("beorn.response.validation_failed", True)
                self.span_helper.add_error_attributes(
                    span=span,
                    error_category="DATA_VALIDATION_ERROR",
                    error_message="Beorn response validation failed - insufficient elements"
                )
        
        return is_valid

