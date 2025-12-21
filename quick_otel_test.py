#!/usr/bin/env python
"""
Quick test to verify OpenTelemetry imports are working.
Run this from the project root directory.
"""

import sys
import os

# Add model-definitions to path
sys.path.append("model-definitions")
if os.path.exists("seefa-om/mdso-alloy/charter_sensor_templates/model-definitions"):
    sys.path.append("seefa-om/mdso-alloy/charter_sensor_templates/model-definitions")

print("Testing OpenTelemetry imports...\n")

# Test 1: Basic OpenTelemetry
try:
    from opentelemetry import trace
    print("✓ OpenTelemetry trace module imported")
except ImportError as e:
    print(f"✗ OpenTelemetry not installed: {e}")
    sys.exit(1)

# Test 2: OTelMixin
try:
    from scripts.otel.otel_mixin import OTelMixin
    print("✓ OTelMixin imported")
    print(f"  Has create_root_span: {hasattr(OTelMixin, 'create_root_span')}")
except ImportError as e:
    print(f"✗ OTelMixin import failed: {e}")
    sys.exit(1)

# Test 3: CommonPlan
try:
    from scripts.common_plan import CommonPlan, OTEL_AVAILABLE
    print(f"✓ CommonPlan imported")
    print(f"  OTEL_AVAILABLE: {OTEL_AVAILABLE}")
    print(f"  Has create_root_span: {hasattr(CommonPlan, 'create_root_span')}")
    
    if hasattr(CommonPlan, 'create_root_span'):
        print(f"  create_root_span is callable: {callable(getattr(CommonPlan, 'create_root_span', None))}")
    
except ImportError as e:
    print(f"✗ CommonPlan import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check inheritance
print(f"\nCommonPlan MRO (Method Resolution Order):")
for i, cls in enumerate(CommonPlan.__mro__):
    marker = " → Has create_root_span" if hasattr(cls, 'create_root_span') else ""
    print(f"  {i}. {cls.__name__}{marker}")

print("\n✓ All imports successful!")

