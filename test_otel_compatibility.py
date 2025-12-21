#!/usr/bin/env python
"""
Test OpenTelemetry compatibility with existing package versions.

This script tests if OpenTelemetry works with the existing package versions
in requirements_python38.txt before deciding whether to update them.
"""

import sys
import importlib

def test_import(module_name, description):
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description}: Available")
        return True
    except ImportError as e:
        print(f"❌ {description}: Failed - {e}")
        return False

def test_package_version(package_name, min_version=None):
    """Test if a package is installed and optionally check version."""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name}: {version}")
        
        if min_version:
            from packaging import version as pkg_version
            if pkg_version.parse(version) >= pkg_version.parse(min_version):
                print(f"   ✓ Version {version} >= {min_version}")
            else:
                print(f"   ⚠️  Version {version} < {min_version} (may need update)")
        
        return True
    except ImportError as e:
        print(f"❌ {package_name}: Not available - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {package_name}: Error checking version - {e}")
        return False

def test_opentelemetry_basic():
    """Test basic OpenTelemetry functionality."""
    print("\n" + "=" * 60)
    print("Testing OpenTelemetry Basic Functionality")
    print("=" * 60)
    
    results = {}
    
    # Test core imports
    results['opentelemetry'] = test_import('opentelemetry', 'OpenTelemetry core')
    results['opentelemetry.trace'] = test_import('opentelemetry.trace', 'OpenTelemetry trace')
    results['opentelemetry.sdk'] = test_import('opentelemetry.sdk.trace', 'OpenTelemetry SDK')
    
    # Test exporter
    results['otlp_exporter'] = test_import(
        'opentelemetry.exporter.otlp.proto.http.trace_exporter',
        'OTLP HTTP exporter'
    )
    
    # Test instrumentation
    results['instrumentation'] = test_import(
        'opentelemetry.instrumentation',
        'OpenTelemetry instrumentation'
    )
    
    return all(results.values())

def test_dependencies():
    """Test dependency packages."""
    print("\n" + "=" * 60)
    print("Testing Dependency Packages")
    print("=" * 60)
    
    results = {}
    
    # Test existing packages (with current versions)
    results['certifi'] = test_package_version('certifi')
    results['requests'] = test_package_version('requests')
    results['urllib3'] = test_package_version('urllib3')
    results['idna'] = test_package_version('idna')
    results['typing_extensions'] = test_package_version('typing_extensions')
    results['charset_normalizer'] = test_package_version('charset_normalizer')
    
    return results

def test_opentelemetry_functionality():
    """Test actual OpenTelemetry functionality."""
    print("\n" + "=" * 60)
    print("Testing OpenTelemetry Functionality")
    print("=" * 60)
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
        
        # Create tracer provider
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        
        # Add console exporter
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Get tracer and create span
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.attribute", "test_value")
            print("✅ Successfully created and configured tracer")
            print("✅ Successfully created test span")
            print("✅ Successfully set span attribute")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenTelemetry functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_https_connection():
    """Test HTTPS connection (uses certifi)."""
    print("\n" + "=" * 60)
    print("Testing HTTPS Connection (certifi)")
    print("=" * 60)
    
    try:
        import requests
        import certifi
        
        # Test HTTPS connection
        response = requests.get('https://www.google.com', timeout=5)
        print(f"✅ HTTPS connection successful (status: {response.status_code})")
        print(f"   Using certifi version: {certifi.__version__}")
        return True
        
    except Exception as e:
        print(f"❌ HTTPS connection failed: {e}")
        return False

def test_idn_support():
    """Test IDN (Internationalized Domain Names) support."""
    print("\n" + "=" * 60)
    print("Testing IDN Support (idna)")
    print("=" * 60)
    
    try:
        import idna
        import requests
        
        # Test IDN encoding
        domain = "münchen.de"  # German domain with umlaut
        encoded = idna.encode(domain)
        decoded = idna.decode(encoded)
        
        print(f"✅ IDN encoding/decoding works")
        print(f"   Original: {domain}")
        print(f"   Encoded: {encoded}")
        print(f"   Decoded: {decoded}")
        print(f"   Using idna version: {idna.__version__}")
        return True
        
    except Exception as e:
        print(f"❌ IDN test failed: {e}")
        return False

def main():
    """Run all compatibility tests."""
    print("=" * 60)
    print("OpenTelemetry Compatibility Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print()
    
    results = {}
    
    # Test dependencies
    dep_results = test_dependencies()
    results.update(dep_results)
    
    # Test OpenTelemetry basic imports
    results['otel_basic'] = test_opentelemetry_basic()
    
    # Test OpenTelemetry functionality
    results['otel_functionality'] = test_opentelemetry_functionality()
    
    # Test HTTPS (certifi)
    results['https'] = test_https_connection()
    
    # Test IDN (idna)
    results['idn'] = test_idn_support()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! OpenTelemetry should work with existing package versions.")
        print("   Recommendation: Keep existing package versions in requirements_python38.txt")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        print("   Recommendation: Investigate failures before updating package versions")
        return 1

if __name__ == "__main__":
    sys.exit(main())

