# Test Sample Logs

This directory contains sample MDSO logs for testing the enhanced Alloy configuration.

## Sample Files

| File | Description | Key Fields Tested |
|------|-------------|------------------|
| `01-circuit-creation.log` | Normal circuit provisioning workflow | circuit_id, resource_id, device_fqdn, vendor, orch_state, service_type |
| `02-error-scenarios.log` | Error conditions and failures | error_code, severity (ERROR/FATAL/WARN), management_ip |
| `03-multi-vendor.log` | Multiple network vendors | vendor (cisco, juniper, adva, rad), device_fqdn |
| `04-service-types.log` | Different service types | service_type (ELAN, ELINE, FIA, VOICE, VIDEO) |
| `05-full-lifecycle.log` | Complete lifecycle (create/update/delete) | orch_state (CREATE/UPDATE/DELETE states) |

## How to Use

### Option 1: Inject into Live System

```bash
# On MDSO server (159.56.4.37)
cat 01-circuit-creation.log | sudo tee -a /var/log/ciena/blueplanet.log

# Wait 10-15 seconds for processing
sleep 15

# Check Alloy logs
docker logs --tail 20 alloy-mdso
```

### Option 2: Test Regex Locally

```bash
# Test circuit_id extraction
grep -oP '(?i)circuit[:\s]+\K\d+\.\S+' 01-circuit-creation.log

# Test resource_id extraction
grep -oP '(?i)resource[:\s]+\K[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' 01-circuit-creation.log

# Test vendor extraction
grep -oP '(?i)vendor[:\s]+\K(?:juniper|adva|cisco|rad)' 03-multi-vendor.log

# Test error code extraction
grep -oP 'DE-\d+|DEF-\d+|ERR-\d+' 02-error-scenarios.log
```

### Option 3: Validate in Loki

After injecting logs, query Loki:

```bash
# On Meta server (159.56.4.94)
# Query for logs with circuit_id
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso", circuit_id="80.L1XX.005054..CHTR"}' | jq

# Query for logs with vendor
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso", vendor="juniper"}' | jq

# Query for error logs
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso", severity="ERROR"}' | jq
```

## Expected Field Extractions

### 01-circuit-creation.log

Expected to extract:
- **7 lines** total
- **circuit_id**: `80.L1XX.005054..CHTR` (lines 1, 3, 6, 7)
- **resource_id**: `550e8400-e29b-41d4-a716-446655440000` (line 1)
- **product_id**: `450e7500-d19b-31c4-b716-336644330000` (line 4)
- **device_fqdn**: `JFVLINBJ2CW.CHTRSE.COM` (lines 2, 5)
- **device_tid**: `JFVLINBJ2CW` (lines 2, 5)
- **vendor**: `juniper` (line 2)
- **orch_state**: `CREATE_IN_PROGRESS` (line 3), `CREATE_COMPLETE` (line 6)
- **service_type**: `ELAN` (line 4)
- **product_type**: `service_mapper` (lines 1, 4, 7), `resource_agent` (lines 2, 5), `orchestration_engine` (lines 3, 6)

### 02-error-scenarios.log

Expected to extract:
- **7 lines** total
- **error_code**: `DE-1000` (line 1), `DEF-456` (line 4), `ERR-2000` (line 6)
- **severity**: `ERROR` (lines 1, 6), `FATAL` (line 2), `WARN` (line 3), `DEBUG` (line 5)
- **circuit_id**: `80.L1XX.006789..CHTR` (lines 1, 4, 6)
- **device_fqdn**: `ABCDEFGH01.CHTRSE.COM` (line 2)
- **vendor**: `adva` (line 2)
- **management_ip**: `10.20.30.40` (line 2)
- **orch_state**: `CREATE_FAILED` (line 3)

### 03-multi-vendor.log

Expected to extract:
- **9 lines** total
- **vendor**: `cisco` (line 1), `juniper` (line 3), `adva` (line 5), `rad` (line 7)
- **device_fqdn**: 4 different devices
- **device_tid**: 4 different TIDs (10 chars each)
- **circuit_id**: 4 different circuits

### 04-service-types.log

Expected to extract:
- **10 lines** total
- **service_type**: `ELAN`, `ELINE`, `FIA`, `VOICE`, `VIDEO` (each appears twice)
- **circuit_id**: 5 different circuits
- **resource_id**: 5 different UUIDs

### 05-full-lifecycle.log

Expected to extract:
- **17 lines** total
- **orch_state**:
  - `CREATE_IN_PROGRESS` (line 2)
  - `CREATE_COMPLETE` (line 7)
  - `UPDATE_IN_PROGRESS` (line 10)
  - `UPDATE_COMPLETE` (line 12)
  - `DELETE_IN_PROGRESS` (line 14)
  - `DELETE_COMPLETE` (line 16)
- **circuit_id**: `80.L1XX.200001..CHTR` (appears in 11 lines)
- **resource_id**: `888e8800-f88f-88f8-f888-888888880000` (lines 2, 14)
- **product_id**: `999e9900-g99g-99g9-g999-999999990000` (line 3)
- **device_fqdn**: `TESTDEVICE.CHTRSE.COM` (lines 4, 6, 11, 15)
- **vendor**: `juniper` (line 4)
- **management_ip**: `192.168.100.50` (line 4)
- **service_type**: `ELAN` (line 5)

## Quick Validation

Run this to quickly validate all extractions:

```bash
#!/bin/bash
echo "=== Circuit IDs ==="
grep -hoP '(?i)circuit[:\s]+\K\d+\.\S+' *.log | sort -u

echo -e "\n=== Resource IDs ==="
grep -hoP '(?i)resource[:\s]+\K[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' *.log | sort -u

echo -e "\n=== Vendors ==="
grep -hoP '(?i)vendor[:\s]+\K(?:juniper|adva|cisco|rad)' *.log | sort -u

echo -e "\n=== Error Codes ==="
grep -hoP 'DE-\d+|DEF-\d+|ERR-\d+' *.log | sort -u

echo -e "\n=== Service Types ==="
grep -hoP '(?i)(?:service[:\s]+|type[:\s]+)\K(?:ELAN|ELINE|FIA|VOICE|VIDEO)' *.log | sort -u

echo -e "\n=== Severity Levels ==="
grep -hoP '(?i)\b(?:ERROR|FATAL|CRITICAL|WARNING|WARN|INFO|DEBUG|TRACE)\b' *.log | sort -u
```

## Integration with CI/CD

These samples can be used for automated testing:

```bash
#!/bin/bash
# Example: automated-test.sh

TEST_DIR="./test-samples"
EXPECTED_EXTRACTIONS=50  # Total expected field extractions across all files

# Inject all test logs
for file in $TEST_DIR/*.log; do
  echo "Injecting $file..."
  cat "$file" | sudo tee -a /var/log/ciena/blueplanet.log
done

# Wait for processing
sleep 30

# Query Loki and count extractions
ACTUAL_EXTRACTIONS=$(curl -s -G 'http://159.56.4.94:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=100' | \
  jq '[.data.result[].stream | select(.circuit_id != "" or .vendor != "" or .error_code != "")] | length')

echo "Expected: $EXPECTED_EXTRACTIONS"
echo "Actual: $ACTUAL_EXTRACTIONS"

if [ "$ACTUAL_EXTRACTIONS" -ge "$EXPECTED_EXTRACTIONS" ]; then
  echo "✓ Test PASSED"
  exit 0
else
  echo "✗ Test FAILED"
  exit 1
fi
```

## Notes

- All timestamps use format: `Nov 16 HH:MM:SS`
- Hostname is always: `mdso-host`
- Process name is always: `CIENA[PID]`
- Real MDSO logs may have variations - adjust regex patterns as needed
- Test with actual production log samples before going live
