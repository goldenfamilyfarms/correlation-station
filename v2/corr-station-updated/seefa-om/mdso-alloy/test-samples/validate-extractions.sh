#!/bin/bash
# Validate field extractions from test sample logs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  Enhanced Alloy Config - Field Extraction Test"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

test_extraction() {
  local pattern="$1"
  local file="$2"
  local expected_count="$3"
  local field_name="$4"

  actual_count=$(grep -oP "$pattern" "$file" 2>/dev/null | wc -l)

  if [ "$actual_count" -ge "$expected_count" ]; then
    echo -e "${GREEN}✓${NC} $field_name in $file: $actual_count matches (expected >= $expected_count)"
    ((passed++))
  else
    echo -e "${RED}✗${NC} $field_name in $file: $actual_count matches (expected >= $expected_count)"
    ((failed++))
  fi
}

echo "Testing 01-circuit-creation.log..."
test_extraction '(?i)circuit[:\s]+\K\d+\.\S+' '01-circuit-creation.log' 4 'circuit_id'
test_extraction '(?i)resource[:\s]+\K[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' '01-circuit-creation.log' 1 'resource_id'
test_extraction '(?i)(?:device|on)\s+[A-Z0-9]{10}\.[A-Z0-9\.]+' '01-circuit-creation.log' 2 'device_fqdn'
test_extraction '(?i)vendor[:\s]+\K(?:juniper|adva|cisco|rad)' '01-circuit-creation.log' 1 'vendor'
test_extraction '(?:CREATE|DELETE|UPDATE|ACTIVATE|DEACTIVATE)_IN_PROGRESS|(?:CREATE|DELETE|UPDATE)_COMPLETE|(?:CREATE|DELETE|UPDATE)_FAILED' '01-circuit-creation.log' 2 'orch_state'
echo ""

echo "Testing 02-error-scenarios.log..."
test_extraction 'DE-\d+|DEF-\d+|ERR-\d+' '02-error-scenarios.log' 3 'error_code'
test_extraction '(?i)\b(?:ERROR|FATAL|CRITICAL|WARNING|WARN|INFO|DEBUG)\b' '02-error-scenarios.log' 5 'severity'
test_extraction '(?i)circuit[:\s]+\K\d+\.\S+' '02-error-scenarios.log' 3 'circuit_id'
test_extraction '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' '02-error-scenarios.log' 1 'management_ip'
echo ""

echo "Testing 03-multi-vendor.log..."
test_extraction '(?i)vendor[:\s]+\K(?:juniper|adva|cisco|rad)' '03-multi-vendor.log' 4 'vendor (4 types)'
test_extraction '(?i)(?:device|on)\s+[A-Z0-9]{10}\.[A-Z0-9\.]+' '03-multi-vendor.log' 4 'device_fqdn'
test_extraction '(?i)circuit[:\s]+\K\d+\.\S+' '03-multi-vendor.log' 4 'circuit_id'
echo ""

echo "Testing 04-service-types.log..."
test_extraction '(?i)(?:service[:\s]+|type[:\s]+)?(?:ELAN|ELINE|FIA|VOICE|VIDEO)' '04-service-types.log' 5 'service_type'
test_extraction '(?i)circuit[:\s]+\K\d+\.\S+' '04-service-types.log' 5 'circuit_id'
test_extraction '(?i)resource[:\s]+\K[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' '04-service-types.log' 5 'resource_id'
echo ""

echo "Testing 05-full-lifecycle.log..."
test_extraction '(?i)circuit[:\s]+\K\d+\.\S+' '05-full-lifecycle.log' 10 'circuit_id'
test_extraction '(?:CREATE|DELETE|UPDATE|ACTIVATE|DEACTIVATE)_IN_PROGRESS|(?:CREATE|DELETE|UPDATE)_COMPLETE|(?:CREATE|DELETE|UPDATE)_FAILED' '05-full-lifecycle.log' 6 'orch_state (lifecycle)'
test_extraction '(?i)(?:device|on)\s+[A-Z0-9]{10}\.[A-Z0-9\.]+' '05-full-lifecycle.log' 4 'device_fqdn'
test_extraction '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' '05-full-lifecycle.log' 1 'management_ip'
echo ""

echo "================================================"
echo "  Summary"
echo "================================================"
echo -e "${GREEN}Passed:${NC} $passed"
if [ $failed -gt 0 ]; then
  echo -e "${RED}Failed:${NC} $failed"
  echo ""
  echo -e "${YELLOW}Some tests failed. Review regex patterns in config.alloy${NC}"
  exit 1
else
  echo -e "${GREEN}All tests passed!${NC}"
  echo ""
  echo "Field extraction patterns are working correctly."
  echo "Ready to deploy to production."
  exit 0
fi
