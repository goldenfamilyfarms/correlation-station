#!/usr/bin/env python
"""
Test script for environment_logger.py

This script demonstrates the environment logger functionality and can be used
to verify that it works correctly before integration into scriptplan.
"""

import logging
import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment_logger import EnvironmentLogger, log_scriptplan_environment


def setup_test_logger():
    """Set up a logger for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("test_environment_logger")


def test_basic_logging():
    """Test basic environment logging without dependencies."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Environment Logging (without pip-compile)")
    print("=" * 80 + "\n")

    logger = setup_test_logger()
    env_logger = EnvironmentLogger(logger)

    # Log environment without dependencies
    env_info = env_logger.log_environment(include_dependencies=False)

    print("\n" + "=" * 80)
    print("TEST 1 COMPLETE")
    print("=" * 80 + "\n")

    return env_info


def test_with_dependencies():
    """Test environment logging with pip-compile dependencies."""
    print("\n" + "=" * 80)
    print("TEST 2: Environment Logging with pip-compile Dependencies")
    print("=" * 80 + "\n")

    logger = setup_test_logger()

    # Log environment with dependencies
    env_info = log_scriptplan_environment(
        logger=logger,
        include_dependencies=True,
        otel_span=None
    )

    print("\n" + "=" * 80)
    print("TEST 2 COMPLETE")
    print("=" * 80 + "\n")

    return env_info


def test_environment_info_collection():
    """Test just the environment info collection without logging."""
    print("\n" + "=" * 80)
    print("TEST 3: Environment Info Collection (Structured Data)")
    print("=" * 80 + "\n")

    logger = setup_test_logger()
    env_logger = EnvironmentLogger(logger)

    # Collect environment info
    env_info = env_logger.collect_environment_info()

    # Print structured data
    import json
    print(json.dumps(env_info, indent=2, default=str))

    print("\n" + "=" * 80)
    print("TEST 3 COMPLETE")
    print("=" * 80 + "\n")

    return env_info


def test_pip_compile_only():
    """Test just the pip-compile functionality."""
    print("\n" + "=" * 80)
    print("TEST 4: pip-compile Dependencies Only")
    print("=" * 80 + "\n")

    logger = setup_test_logger()
    env_logger = EnvironmentLogger(logger)

    # Get pip-compiled dependencies
    deps, error = env_logger.get_pip_compiled_dependencies()

    if deps:
        print("✓ Successfully compiled dependencies:")
        print("-" * 80)
        print(deps)
        print("-" * 80)
    else:
        print(f"✗ Failed to compile dependencies: {error}")

    print("\n" + "=" * 80)
    print("TEST 4 COMPLETE")
    print("=" * 80 + "\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("ENVIRONMENT LOGGER TEST SUITE")
    print("=" * 80 + "\n")

    # Test 1: Basic logging without dependencies (fast)
    try:
        test_basic_logging()
    except Exception as e:
        print(f"ERROR in Test 1: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Environment info collection
    try:
        test_environment_info_collection()
    except Exception as e:
        print(f"ERROR in Test 3: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: pip-compile only (may be slow)
    try:
        test_pip_compile_only()
    except Exception as e:
        print(f"ERROR in Test 4: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Full logging with dependencies (may be slow)
    print("\nNOTE: The next test may take 30-60 seconds due to pip-compile...")
    try:
        test_with_dependencies()
    except Exception as e:
        print(f"ERROR in Test 2: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
