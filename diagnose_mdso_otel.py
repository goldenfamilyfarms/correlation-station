#!/usr/bin/env python
"""
Diagnostic script to check OpenTelemetry installation on MDSO server.

Run this in the MDSO virtual environment to diagnose issues.
"""

import sys
import os

def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def check_python_env():
    print_section("Python Environment")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script file: {__file__ if '__file__' in globals() else 'N/A'}")

def check_sys_path():
    print_section("sys.path (first 15 entries)")
    for i, path in enumerate(sys.path[:15]):
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"  {i}. {exists} {path}")
    
    # Check for model-definitions
    model_defs_found = any('model-definitions' in p for p in sys.path)
    print(f"\n  model-definitions in sys.path: {'✅ Yes' if model_defs_found else '❌ No'}")

def check_package_installation():
    print_section("Package Installation Check")
    
    packages_to_check = [
        ('opentelemetry', 'opentelemetry'),
        ('opentelemetry-api', 'opentelemetry'),
        ('opentelemetry-sdk', 'opentelemetry.sdk'),
        ('structlog', 'structlog'),
        ('pyroscope', 'pyroscope'),
    ]
    
    for package_name, import_name in packages_to_check:
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"✅ {package_name}: {version}")
        except ImportError as e:
            print(f"❌ {package_name}: Not installed - {e}")

def check_otel_imports():
    print_section("OpenTelemetry Import Test")
    
    imports = [
        ('opentelemetry.trace', 'from opentelemetry import trace'),
        ('opentelemetry.sdk.trace', 'from opentelemetry.sdk.trace import TracerProvider'),
        ('structlog', 'import structlog'),
        ('pyroscope', 'import pyroscope'),
    ]
    
    for module_name, import_stmt in imports:
        try:
            exec(import_stmt)
            print(f"✅ {module_name}: Import successful")
        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")

def check_scripts_otel_imports():
    print_section("scripts.otel Import Test")
    
    # First check if model-definitions is in path
    model_defs_in_path = any('model-definitions' in p for p in sys.path)
    if not model_defs_in_path:
        print("⚠️  model-definitions not in sys.path - adding it")
        # Try to add it
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_defs = os.path.dirname(os.path.dirname(script_dir))
        if os.path.exists(model_defs):
            sys.path.insert(0, model_defs)
            print(f"✅ Added {model_defs} to sys.path")
    
    imports = [
        ('scripts.otel.otel_mixin', 'from scripts.otel.otel_mixin import OTelMixin'),
        ('scripts.otel.instrumentation', 'from scripts.otel.instrumentation import inject_correlation_context'),
        ('scripts.otel.otel_mdso_utils', 'from scripts.otel.otel_mdso_utils import MDSOSpanHelper'),
    ]
    
    for module_name, import_stmt in imports:
        try:
            exec(import_stmt)
            print(f"✅ {module_name}: Import successful")
        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")

def check_venv_location():
    print_section("Virtual Environment Location")
    
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        print(f"✅ VIRTUAL_ENV: {venv}")
        site_packages = os.path.join(venv, 'lib', 'python3.10', 'site-packages')
        if os.path.exists(site_packages):
            print(f"✅ site-packages: {site_packages}")
            # Check for opentelemetry
            otel_path = os.path.join(site_packages, 'opentelemetry')
            if os.path.exists(otel_path):
                print(f"✅ OpenTelemetry found in venv")
            else:
                print(f"❌ OpenTelemetry NOT found in venv")
        else:
            print(f"❌ site-packages not found: {site_packages}")
    else:
        print("⚠️  VIRTUAL_ENV not set - may not be in a virtual environment")

def check_requirements_file():
    print_section("Requirements File Check")
    
    # Try to find requirements_cst.txt
    possible_locations = [
        'requirements_cst.txt',
        'model-definitions/requirements_cst.txt',
        '../requirements_cst.txt',
        '../../requirements_cst.txt',
    ]
    
    for loc in possible_locations:
        if os.path.exists(loc):
            print(f"✅ Found: {os.path.abspath(loc)}")
            with open(loc, 'r') as f:
                content = f.read()
                if 'opentelemetry' in content:
                    print("✅ Contains OpenTelemetry packages")
                    # Show OpenTelemetry lines
                    lines = [l for l in content.split('\n') if 'opentelemetry' in l.lower() or 'structlog' in l.lower()]
                    for line in lines[:10]:
                        print(f"   {line}")
                else:
                    print("❌ Does NOT contain OpenTelemetry packages")
            return
    
    print("❌ Could not find requirements_cst.txt")

def main():
    print("=" * 60)
    print("MDSO OpenTelemetry Diagnostic Script")
    print("=" * 60)
    
    check_python_env()
    check_sys_path()
    check_venv_location()
    check_package_installation()
    check_otel_imports()
    check_scripts_otel_imports()
    check_requirements_file()
    
    print_section("Summary")
    print("If you see ❌ marks above, those are the issues to fix.")
    print("\nCommon fixes:")
    print("1. Ensure requirements_cst.txt has OpenTelemetry packages")
    print("2. Ensure PYPI index URLs are correct")
    print("3. Ensure MDSO is using the correct requirements file")
    print("4. Check that PYPI server is accessible")

if __name__ == "__main__":
    main()

