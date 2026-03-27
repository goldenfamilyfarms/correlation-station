#!/bin/bash
# Integrate OTel instrumentation into MDSO product
# Run this on the MDSO server after deploying

set -e

echo "=== MDSO Product OTel Integration Helper ==="
echo ""

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <product-directory> [product-class-name]"
    echo ""
    echo "Examples:"
    echo "  $0 /opt/ciena/bp2/bpso-sensor-templates/scripts/serviceMapper ServiceMapper"
    echo "  $0 /opt/ciena/bp2/bpraadva/scripts AdvaResourceAdapter"
    echo ""
    echo "This script will:"
    echo "  1. Copy otel_instrumentation module to product directory"
    echo "  2. Install dependencies"
    echo "  3. Create a sample integration file"
    echo ""
    exit 1
fi

PRODUCT_DIR="$1"
PRODUCT_CLASS="${2:-YourProduct}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify product directory exists
if [ ! -d "$PRODUCT_DIR" ]; then
    echo "ERROR: Product directory not found: $PRODUCT_DIR"
    exit 1
fi

echo "Product directory: $PRODUCT_DIR"
echo "Product class: $PRODUCT_CLASS"
echo ""

# Copy otel_instrumentation module
echo "→ Copying OTel instrumentation module..."
if [ ! -d "${SCRIPT_DIR}/mdso-instrumentation/otel_instrumentation" ]; then
    echo "ERROR: OTel instrumentation not found at ${SCRIPT_DIR}/mdso-instrumentation/otel_instrumentation"
    exit 1
fi

sudo cp -r "${SCRIPT_DIR}/mdso-instrumentation/otel_instrumentation" "$PRODUCT_DIR/"
echo "  ✓ Copied to $PRODUCT_DIR/otel_instrumentation/"

# Install dependencies
echo ""
echo "→ Installing dependencies..."
if command -v pip &> /dev/null; then
    pip install -r "$PRODUCT_DIR/otel_instrumentation/requirements.txt" --quiet
    echo "  ✓ Dependencies installed"
else
    echo "WARNING: pip not found. Install dependencies manually:"
    echo "  pip install -r $PRODUCT_DIR/otel_instrumentation/requirements.txt"
fi

# Create sample integration file
SAMPLE_FILE="$PRODUCT_DIR/otel_integration_example.py"
echo ""
echo "→ Creating sample integration file..."

cat > "$SAMPLE_FILE" <<EOF
"""
Sample OTel Integration for ${PRODUCT_CLASS}

This shows how to add OTel instrumentation to your product.
"""

from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.feature_flags import is_otel_enabled
from otel_instrumentation.instrumentation import mdso_span


# BEFORE (existing class)
# class ${PRODUCT_CLASS}(CommonPlan):
#     def run(self):
#         # existing code
#         pass

# AFTER (with OTel)
class ${PRODUCT_CLASS}(CommonPlan, OTelMixin):
    """
    ${PRODUCT_CLASS} with OpenTelemetry instrumentation
    """

    def run(self):
        """Override run() to add OTel root span"""
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()

    # Example: Add span to a specific method
    def process_circuit(self, circuit_id):
        """Process circuit with OTel tracking"""
        if not is_otel_enabled():
            return self._original_process_circuit(circuit_id)

        with mdso_span(
            "mdso.${PRODUCT_CLASS}.process_circuit",
            circuit_id=circuit_id
        ) as span:
            try:
                result = self._original_process_circuit(circuit_id)
                span.set_attribute("success", True)
                return result
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise

    # Example: Use dual logging
    def some_method(self):
        """Example method with dual logging"""
        # This logs to both standard logger AND OTel
        self.otel_log(
            "Processing started",
            level="info",
            circuit_id=self.circuit_id,
            custom_field="value"
        )

        # Your existing code
        # ...

        self.otel_log("Processing completed", level="info")


# Environment variables to set:
# export OTEL_ENABLED=true
# export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# export MDSO_ENV=dev

# For isolated containers (can't reach Alloy directly):
# export OTEL_TRACE_EXPORT_MODE=file
# export OTEL_TRACE_FILE_PATH=/opt/ciena/bp2/alloy-collector/traces.ndjson
EOF

echo "  ✓ Created $SAMPLE_FILE"

# Create environment file
ENV_FILE="$PRODUCT_DIR/otel_env.sh"
cat > "$ENV_FILE" <<'EOF'
#!/bin/bash
# Environment variables for OTel instrumentation
# Source this file before running products: source otel_env.sh

# Enable OTel
export OTEL_ENABLED=true

# OTel endpoint (Alloy collector)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Environment
export MDSO_ENV=dev

# For isolated containers (optional)
# export OTEL_TRACE_EXPORT_MODE=file
# export OTEL_TRACE_FILE_PATH=/opt/ciena/bp2/alloy-collector/traces.ndjson

# Feature flags (optional)
# export OTEL_SAMPLING_ENABLED=true
# export OTEL_SAMPLING_RATE=1.0

echo "OTel environment variables set:"
echo "  OTEL_ENABLED=$OTEL_ENABLED"
echo "  OTEL_EXPORTER_OTLP_ENDPOINT=$OTEL_EXPORTER_OTLP_ENDPOINT"
echo "  MDSO_ENV=$MDSO_ENV"
EOF

chmod +x "$ENV_FILE"
echo "  ✓ Created $ENV_FILE"

# Create test script
TEST_FILE="$PRODUCT_DIR/test_otel_integration.py"
cat > "$TEST_FILE" <<'EOF'
#!/usr/bin/env python3
"""
Test OTel integration

Run this to verify OTel is working in your product.
"""

import os
import sys

# Set environment for testing
os.environ['OTEL_ENABLED'] = 'true'
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'http://localhost:4318'
os.environ['MDSO_ENV'] = 'dev'

# Import OTel components
try:
    from otel_instrumentation.otel_mixin import OTelMixin
    from otel_instrumentation.instrumentation import setup_otel, mdso_span
    from otel_instrumentation.feature_flags import is_otel_enabled
    print("✓ OTel imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nMake sure otel_instrumentation is in the Python path")
    sys.exit(1)

# Test feature flag
if is_otel_enabled():
    print("✓ OTel is enabled")
else:
    print("✗ OTel is disabled")
    sys.exit(1)

# Test tracer initialization
try:
    tracer = setup_otel(service_name="mdso.test", environment="dev")
    print("✓ Tracer initialized")
except Exception as e:
    print(f"✗ Tracer initialization failed: {e}")
    sys.exit(1)

# Test span creation
try:
    with mdso_span("test.span", circuit_id="TEST-123") as span:
        span.set_attribute("test", True)
    print("✓ Span created successfully")
except Exception as e:
    print(f"✗ Span creation failed: {e}")
    sys.exit(1)

print("\n=== OTel Integration Test Passed ===")
print("\nNext steps:")
print("  1. Integrate OTelMixin into your product class")
print("  2. Set environment variables (source otel_env.sh)")
print("  3. Run your product")
print("  4. Check Grafana Tempo for traces")
EOF

chmod +x "$TEST_FILE"
echo "  ✓ Created $TEST_FILE"

echo ""
echo "=== Integration Complete ==="
echo ""
echo "Files created:"
echo "  - $PRODUCT_DIR/otel_instrumentation/ (module)"
echo "  - $SAMPLE_FILE (example)"
echo "  - $ENV_FILE (environment vars)"
echo "  - $TEST_FILE (test script)"
echo ""
echo "Next steps:"
echo ""
echo "1. Test the integration:"
echo "   cd $PRODUCT_DIR"
echo "   python3 test_otel_integration.py"
echo ""
echo "2. Review the example:"
echo "   cat otel_integration_example.py"
echo ""
echo "3. Set environment variables:"
echo "   source otel_env.sh"
echo ""
echo "4. Modify your product class:"
echo "   - Inherit from OTelMixin"
echo "   - Override run() method"
echo "   - See otel_integration_example.py for details"
echo ""
echo "5. Test with a real circuit:"
echo "   - Run product"
echo "   - Check Grafana Tempo: {service.name=\"mdso.${PRODUCT_CLASS,,}\"}"
echo ""
