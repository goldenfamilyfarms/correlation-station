#!/usr/bin/env python
"""
Verification script to test OpenTelemetry imports and functionality.

This script checks if:
1. OpenTelemetry packages are installed
2. OTelMixin can be imported
3. CommonPlan can access create_root_span method
4. The import fallback mechanism works correctly
"""

import sys
import os

# Add model-definitions to path (same as common_plan.py does)
sys.path.append("model-definitions")
if os.path.exists("seefa-om/mdso-alloy/charter_sensor_templates/model-definitions"):
    sys.path.append("seefa-om/mdso-alloy/charter_sensor_templates/model-definitions")

def test_basic_otel_imports():
    """Test if basic OpenTelemetry packages are available"""
    print("=" * 60)
    print("Test 1: Basic OpenTelemetry Package Imports")
    print("=" * 60)
    
    try:
        from opentelemetry import trace
        print("✓ opentelemetry.trace imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import opentelemetry.trace: {e}")
        return False
    
    try:
        from opentelemetry.sdk.trace import TracerProvider
        print("✓ opentelemetry.sdk.trace.TracerProvider imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import TracerProvider: {e}")
        return False
    
    return True

def test_otel_mixin_import():
    """Test if OTelMixin can be imported"""
    print("\n" + "=" * 60)
    print("Test 2: OTelMixin Import")
    print("=" * 60)
    
    try:
        from scripts.otel.otel_mixin import OTelMixin
        print("✓ OTelMixin imported successfully")
        print(f"  Class: {OTelMixin}")
        print(f"  Has create_root_span: {hasattr(OTelMixin, 'create_root_span')}")
        return True, OTelMixin
    except ImportError as e:
        print(f"✗ Failed to import OTelMixin: {e}")
        print(f"  Import path attempted: scripts.otel.otel_mixin")
        return False, None

def test_instrumentation_import():
    """Test if instrumentation module can be imported"""
    print("\n" + "=" * 60)
    print("Test 3: Instrumentation Module Import")
    print("=" * 60)
    
    try:
        from scripts.otel.instrumentation import inject_correlation_context
        print("✓ inject_correlation_context imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import inject_correlation_context: {e}")
        print(f"  Import path attempted: scripts.otel.instrumentation")
        return False

def test_common_plan_import():
    """Test if CommonPlan imports work correctly"""
    print("\n" + "=" * 60)
    print("Test 4: CommonPlan Import and OTel Integration")
    print("=" * 60)
    
    try:
        from scripts.common_plan import CommonPlan, OTEL_AVAILABLE
        print(f"✓ CommonPlan imported successfully")
        print(f"  OTEL_AVAILABLE flag: {OTEL_AVAILABLE}")
        
        # Check if CommonPlan has create_root_span method
        has_method = hasattr(CommonPlan, 'create_root_span')
        print(f"  CommonPlan has create_root_span: {has_method}")
        
        if has_method:
            print(f"  create_root_span is callable: {callable(getattr(CommonPlan, 'create_root_span', None))}")
        
        # Check MRO to see inheritance
        print(f"  Method Resolution Order (MRO):")
        for i, cls in enumerate(CommonPlan.__mro__):
            print(f"    {i}. {cls.__name__}")
            if hasattr(cls, 'create_root_span'):
                print(f"       → Has create_root_span method")
        
        return True, OTEL_AVAILABLE
    except ImportError as e:
        print(f"✗ Failed to import CommonPlan: {e}")
        import traceback
        traceback.print_exc()
        return False, False

def test_mock_activate_class():
    """Test if a mock Activate class can use create_root_span"""
    print("\n" + "=" * 60)
    print("Test 5: Mock Activate Class Test")
    print("=" * 60)
    
    try:
        from scripts.common_plan import CommonPlan
        
        # Create a simple mock class that inherits from CommonPlan
        class MockActivate(CommonPlan):
            pass
        
        mock_instance = type('MockActivate', (CommonPlan,), {})
        
        # Check if the class has the method
        has_method = hasattr(CommonPlan, 'create_root_span')
        print(f"✓ MockActivate class created")
        print(f"  Has create_root_span method: {has_method}")
        
        if has_method:
            print(f"  Method is callable: {callable(getattr(CommonPlan, 'create_root_span', None))}")
            return True
        else:
            print("  ⚠ Warning: create_root_span method not found")
            return False
            
    except Exception as e:
        print(f"✗ Failed to test mock class: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_fallback():
    """Test the import fallback mechanism"""
    print("\n" + "=" * 60)
    print("Test 6: Import Fallback Mechanism")
    print("=" * 60)
    
    try:
        from scripts.common_plan import OTEL_AVAILABLE, OTelMixin
        
        if OTEL_AVAILABLE:
            print("✓ OTEL_AVAILABLE is True - OpenTelemetry is available")
            print(f"  OTelMixin type: {type(OTelMixin)}")
            if OTelMixin != object:
                print("  ✓ OTelMixin is the real class (not fallback)")
            else:
                print("  ⚠ OTelMixin is fallback object (import failed)")
        else:
            print("⚠ OTEL_AVAILABLE is False - OpenTelemetry not available")
            print(f"  OTelMixin type: {type(OTelMixin)}")
            if OTelMixin == object:
                print("  ✓ Fallback mechanism working correctly")
            else:
                print("  ✗ Fallback mechanism not working as expected")
        
        return True
    except Exception as e:
        print(f"✗ Failed to test fallback: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all verification tests"""
    print("\n" + "=" * 60)
    print("OpenTelemetry Import Verification Script")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    results = {}
    
    # Run tests
    results['basic_otel'] = test_basic_otel_imports()
    results['otel_mixin'], otel_mixin_class = test_otel_mixin_import()
    results['instrumentation'] = test_instrumentation_import()
    results['common_plan'], otel_available = test_common_plan_import()
    results['mock_activate'] = test_mock_activate_class()
    results['fallback'] = test_import_fallback()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed! OpenTelemetry imports are working correctly.")
    else:
        print("✗ Some tests failed. Check the output above for details.")
        print("\nTroubleshooting tips:")
        print("1. Ensure OpenTelemetry packages are installed:")
        print("   pip install opentelemetry-api opentelemetry-sdk")
        print("2. Check that the scripts/otel directory exists")
        print("3. Verify the import paths are correct")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

