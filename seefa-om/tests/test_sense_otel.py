"""
Test SENSE OpenTelemetry Configuration
Validates otel_sense.py setup and trace generation
"""

import sys
import time
from pathlib import Path

# Add sense-apps to path
sys.path.insert(0, str(Path(__file__).parent / "seefa-om" / "sense-apps" / "arda"))

from arda_app.common.otel.otel_sense import (
    setup_otel_sense,
    set_mdso_correlation,
    traced,
    get_current_span,
)

def test_basic_setup():
    """Test basic OTel setup"""
    print("✓ Testing basic OTel setup...")
    
    tracer = setup_otel_sense(
        service_name="test-arda",
        service_version="1.0.0",
        environment="dev",
        correlation_gateway="http://austx-mdso-logs-02.chtrse.com:8080"
    )
    
    print(f"  Tracer created: {tracer}")
    print("  ✓ Basic setup successful\n")
    return tracer


def test_manual_span(tracer):
    """Test manual span creation"""
    print("✓ Testing manual span creation...")
    
    with tracer.start_as_current_span("test.manual_span") as span:
        span.set_attribute("test.type", "manual")
        span.set_attribute("test.value", 42)
        
        # Add MDSO correlation
        set_mdso_correlation(
            circuit_id="80.L1XX.005054..CHTR",
            resource_id="test-resource-123",
            fqdn="TEST-DEVICE.CHTRSE.COM",
            vendor="juniper"
        )
        
        print(f"  Span ID: {format(span.get_span_context().span_id, '016x')}")
        print(f"  Trace ID: {format(span.get_span_context().trace_id, '032x')}")
        print("  ✓ Manual span successful\n")


@traced("test.decorated_function", {"operation": "test"})
def test_decorated_function():
    """Test decorated function"""
    print("✓ Testing @traced decorator...")
    
    span = get_current_span()
    if span and span.is_recording():
        print(f"  Span ID: {format(span.get_span_context().span_id, '016x')}")
        print("  ✓ Decorator successful\n")
    
    return "success"


@traced("test.async_function")
async def test_async_function():
    """Test async decorated function"""
    print("✓ Testing async @traced decorator...")
    
    span = get_current_span()
    if span and span.is_recording():
        print(f"  Span ID: {format(span.get_span_context().span_id, '016x')}")
        print("  ✓ Async decorator successful\n")
    
    return "async_success"


def test_nested_spans(tracer):
    """Test nested span creation"""
    print("✓ Testing nested spans...")
    
    with tracer.start_as_current_span("test.parent") as parent:
        parent.set_attribute("span.level", "parent")
        
        with tracer.start_as_current_span("test.child") as child:
            child.set_attribute("span.level", "child")
            
            with tracer.start_as_current_span("test.grandchild") as grandchild:
                grandchild.set_attribute("span.level", "grandchild")
                
                print(f"  Parent Span ID: {format(parent.get_span_context().span_id, '016x')}")
                print(f"  Child Span ID: {format(child.get_span_context().span_id, '016x')}")
                print(f"  Grandchild Span ID: {format(grandchild.get_span_context().span_id, '016x')}")
                print("  ✓ Nested spans successful\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("SENSE OpenTelemetry Configuration Test")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: Basic setup
        tracer = test_basic_setup()
        
        # Test 2: Manual span
        test_manual_span(tracer)
        
        # Test 3: Decorated function
        test_decorated_function()
        
        # Test 4: Async function
        import asyncio
        asyncio.run(test_async_function())
        
        # Test 5: Nested spans
        test_nested_spans(tracer)
        
        # Wait for spans to export
        print("⏳ Waiting for spans to export (5 seconds)...")
        time.sleep(5)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nCheck traces at:")
        print("  http://austx-mdso-logs-02.chtrse.com/grafana/explore")
        print("  Service: test-arda")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
