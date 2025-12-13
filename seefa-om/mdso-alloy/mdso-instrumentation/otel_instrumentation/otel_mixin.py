"""
OTel Mixin for MDSO Scriptplan Products
Provides non-invasive OpenTelemetry instrumentation

Based on: OTEL_IMPLEMENTATION_STRATEGY.md
"""
import os
import logging
from typing import Optional, Dict, Any
from opentelemetry import trace

from otel_instrumentation.instrumentation import (
    setup_otel,
    get_otel_logger,
    inject_correlation_context,
    mdso_span,
    extract_correlation_context
)
from otel_instrumentation.otel_mdso_utils import (
    MDSOSpanHelper,
    ErrorPatternMatcher
)

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
        # Prevent double initialization
        if hasattr(self, '_otel_initialized') and self._otel_initialized:
            return

        # Get product/resource type from class name
        product_type = self.__class__.__name__
        service_name = f"mdso.{product_type.lower()}"

        # Get environment from instance or env var
        environment = getattr(self, 'environment', None) or os.getenv("MDSO_ENV", "dev")

        # Setup OTel tracer
        self.tracer = setup_otel(
            service_name=service_name,
            environment=environment
        )

        # Setup structured logger
        self.otel_logger = get_otel_logger(service_name)

        # Helper for span management
        self.span_helper = MDSOSpanHelper()
        self.error_matcher = ErrorPatternMatcher()

        # Mark as initialized
        self._otel_initialized = True

        logger.info(f"OTel initialized for {product_type}", service_name=service_name, environment=environment)

    def create_root_span(self, operation_name: Optional[str] = None):
        """
        Create root span for product execution
        
        Usage:
            with self.create_root_span():
                return super().run()
        """
        if not hasattr(self, '_otel_initialized') or not self._otel_initialized:
            self.__init_otel__()

        product_name = self.__class__.__name__
        span_name = operation_name or f"mdso.product.{product_name}"

        # Extract correlation context from instance attributes
        correlation_attrs = {}
        if hasattr(self, 'circuit_id') and self.circuit_id:
            correlation_attrs['circuit_id'] = self.circuit_id
        if hasattr(self, 'resource_id') and self.resource_id:
            correlation_attrs['resource_id'] = self.resource_id
        if hasattr(self, 'product_id') and self.product_id:
            correlation_attrs['product_id'] = self.product_id

        # Inject correlation context
        if correlation_attrs:
            inject_correlation_context(**correlation_attrs)

        return mdso_span(
            name=span_name,
            **correlation_attrs
        )

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

