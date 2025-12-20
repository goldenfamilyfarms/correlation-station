#!/usr/bin/env python3
"""
Diagnostic script to test file-based trace export.

This script tests whether traces can be written to /opt/ciena/bp2/alloy-collector/traces.ndjson.
Run this script from the MDSO script environment to diagnose why logs aren't appearing.

Usage:
    python test_file_export.py
    python test_file_export.py --trace-log-dir /custom/path
"""

import sys
import os
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import instrumentation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from instrumentation import test_file_export, setup_otel, DEFAULT_TRACE_LOG_DIR
    from opentelemetry import trace
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure OpenTelemetry packages are installed:")
    logger.error("  pip install opentelemetry-api opentelemetry-sdk")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test file-based trace export")
    parser.add_argument(
        "--trace-log-dir",
        type=str,
        default=None,
        help=f"Trace log directory (default: {DEFAULT_TRACE_LOG_DIR})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("File Export Diagnostic Test")
    logger.info("=" * 60)
    
    # Run the test
    result = test_file_export(trace_log_dir=args.trace_log_dir)
    
    # Print results
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Results")
    logger.info("=" * 60)
    logger.info(f"Success: {result['success']}")
    logger.info(f"File Path: {result.get('file_path', 'N/A')}")
    logger.info(f"File Exists: {result.get('file_exists', False)}")
    logger.info(f"File Writable: {result.get('file_writable', False)}")
    logger.info(f"File Size: {result.get('file_size', 0)} bytes")
    logger.info(f"Test Span Written: {result.get('test_span_written', False)}")
    
    if result.get('error'):
        logger.error(f"Error: {result['error']}")
    
    logger.info("=" * 60)
    
    # Exit with appropriate code
    if result['success'] and result.get('test_span_written', False):
        logger.info("✓ Test PASSED - File export is working correctly")
        return 0
    else:
        logger.error("✗ Test FAILED - File export is not working")
        return 1


if __name__ == "__main__":
    sys.exit(main())

