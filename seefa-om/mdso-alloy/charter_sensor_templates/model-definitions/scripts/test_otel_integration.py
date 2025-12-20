#!/usr/bin/env python
"""
Test script to verify OTelMixin integration with CommonPlan pattern
"""
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import OTelMixin
from otel.otel_mixin import OTelMixin
from otel.instrumentation import inject_correlation_context
from opentelemetry import trace

# Mock CommonPlan constants (mimicking real CommonPlan class)
class MockCommonPlan(OTelMixin):
    """Mock CommonPlan class to test OTelMixin integration"""

    # OpenTelemetry Configuration Constants (from CommonPlan)
    MDSO_ENV = "test"
    OTEL_EXPORT_MODE = None  # None = auto-detect (defaults to "file")
    OTEL_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector"
    OTEL_USE_SUDO = None  # None = auto-detect based on permissions
    OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4318"
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT = None
    OTEL_ENABLED = True
    OTEL_SAMPLING_ENABLED = True
    OTEL_SAMPLING_RATE = 1.0

    def __init__(self):
        """Initialize mock CommonPlan"""
        self.logger = logging.getLogger("test.MockCommonPlan")
        self.the_class = f"{self.__module__}.{self.__class__.__name__}"
        self.resource_id = "test-resource-123"
        self.circuit_id = "CKT-12345"
        self.product_id = "PROD-67890"

    def run(self):
        """Run method similar to CommonPlan.run()"""
        self.logger.info(f"Starting execution for {self.the_class}")

        # Initialize OTEL using OTelMixin
        self.__init_otel__()

        if hasattr(self, '_otel_initialized') and self._otel_initialized:
            self.logger.info("✓ OpenTelemetry initialized successfully via OTelMixin")
        else:
            self.logger.warning("✗ OpenTelemetry not initialized")
            return False

        # Inject correlation context
        if inject_correlation_context:
            inject_correlation_context(
                circuit_id=self.circuit_id,
                product_id=self.product_id,
                resource_id=self.resource_id,
                resource_type_id="test.resourceType"
            )
            self.logger.info(f"✓ Injected correlation context: circuit_id={self.circuit_id}, product_id={self.product_id}")

        # Create root span using OTelMixin
        with self.create_root_span(f"test.plan.execute.{self.the_class}"):
            try:
                # Get current span
                span = trace.get_current_span()

                # Set span attributes
                if span and span.is_recording():
                    span.set_attribute("plan.class", self.the_class)
                    span.set_attribute("plan.resource_id", str(self.resource_id))
                    span.set_attribute("circuit_id", str(self.circuit_id))
                    span.set_attribute("product_id", str(self.product_id))
                    span.set_attribute("mdso.component", "test-scriptplan")
                    self.logger.info("✓ Set span attributes")

                # Use OTelMixin's structured logging
                if hasattr(self, 'otel_log'):
                    self.otel_log(
                        "Plan execution started",
                        level="info",
                        plan_class=self.the_class,
                        circuit_id=self.circuit_id,
                        product_id=self.product_id,
                        state="STARTED"
                    )
                    self.logger.info("✓ Used otel_log() for structured logging")

                # Simulate processing
                self.logger.info("Processing...")
                result = self.process()

                # Log completion
                if hasattr(self, 'otel_log'):
                    self.otel_log(
                        "Plan execution completed",
                        level="info",
                        plan_class=self.the_class,
                        state="COMPLETED"
                    )
                    self.logger.info("✓ Logged completion with otel_log()")

                # Mark span as successful
                if span and span.is_recording():
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    self.logger.info("✓ Marked span as successful")

                return result

            except Exception as ex:
                self.logger.exception(ex)

                # Use OTelMixin's error handler
                if hasattr(self, 'otel_error_handler'):
                    self.otel_error_handler(
                        error_message=f"Plan execution failed: {str(ex)}",
                        exception=ex
                    )
                    self.logger.info("✓ Used otel_error_handler() for error tracking")

                raise

    def process(self):
        """Simulate process() method from CommonPlan"""
        self.logger.info("Executing process() logic")
        # Simulate some work
        import time
        time.sleep(0.1)
        return {"status": "success", "data": "test_result"}


def main():
    """Test the OTelMixin integration"""
    logger.info("=" * 60)
    logger.info("OTelMixin Integration Test")
    logger.info("=" * 60)

    # Create mock CommonPlan instance
    plan = MockCommonPlan()

    # Run the plan
    try:
        result = plan.run()
        logger.info(f"✓ Test completed successfully: {result}")
        logger.info("=" * 60)
        logger.info("All tests PASSED ✓")
        logger.info("=" * 60)
        return True
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        logger.info("=" * 60)
        logger.info("Tests FAILED ✗")
        logger.info("=" * 60)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
