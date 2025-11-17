# Enhanced Alloy Configuration Testing Guide

## Overview

This guide provides comprehensive testing procedures for the enhanced Alloy configuration with structured field extraction.

## Testing Strategy

1. **Unit Tests** - Test individual regex patterns
2. **Sample Log Tests** - Test with realistic MDSO (Multi-Domain Service Orchestrator) log samples
3. **Integration Tests** - Test full pipeline from MDSO to Loki
4. **Validation Tests** - Verify field extraction accuracy
5. **Performance Tests** - Ensure acceptable performance under load

## Prerequisites

- Alloy container running (see DEPLOYMENT-GUIDE-ENHANCED.md)
- Access to MDSO server (159.56.4.37)
- Access to Meta server (159.56.4.94)
- jq installed for JSON parsing

## Sample Test Logs

### Test Log Set 1: Circuit Creation

```bash
# Create test file
cat > /tmp/test-logs.txt <<'EOF'
Nov 16 10:30:15 mdso-host CIENA[1234]: ServiceMapper: Creating circuit 80.L1XX.005054..CHTR with resource 550e8400-e29b-41d4-a716-446655440000
Nov 16 10:30:16 mdso-host CIENA[1234]: ResourceAgent: Configuring device JFVLINBJ2CW.CHTRSE.COM (vendor: juniper)
Nov 16 10:30:17 mdso-host CIENA[1234]: OrchestrationEngine: State changed to CREATE_IN_PROGRESS for circuit 80.L1XX.005054..CHTR
Nov 16 10:30:18 mdso-host CIENA[1234]: ServiceMapper: Service type ELAN configured for product 450e7500-d19b-31c4-b716-336644330000
Nov 16 10:30:19 mdso-host CIENA[1234]: ResourceAgent: INFO: Configuration applied successfully
EOF
```

**Expected Extractions:**

| Log Line | circuit_id | resource_id | device_fqdn | device_tid | vendor | orch_state | service_type | product_id | severity |
|----------|-----------|-------------|-------------|------------|---------|------------|--------------|------------|----------|
| 1 | 80.L1XX.005054..CHTR | 550e8400-e29b-41d4-a716-446655440000 | - | - | - | - | - | - | INFO |
| 2 | - | - | JFVLINBJ2CW.CHTRSE.COM | JFVLINBJ2CW | juniper | - | - | - | INFO |
| 3 | 80.L1XX.005054..CHTR | - | - | - | - | CREATE_IN_PROGRESS | - | - | INFO |
| 4 | - | - | - | - | - | - | ELAN | 450e7500-d19b-31c4-b716-336644330000 | INFO |
| 5 | - | - | - | - | - | - | - | - | INFO |

### Test Log Set 2: Error Scenarios

```bash
cat > /tmp/test-logs-errors.txt <<'EOF'
Nov 16 11:00:01 mdso-host CIENA[5678]: ServiceMapper: ERROR: Failed to create circuit 80.L1XX.006789..CHTR - DE-1000
Nov 16 11:00:02 mdso-host CIENA[5678]: ResourceAgent: FATAL: Cannot connect to device ABCDEFGH01.CHTRSE.COM (vendor: adva) at management IP 10.20.30.40
Nov 16 11:00:03 mdso-host CIENA[5678]: OrchestrationEngine: WARNING: State changed to CREATE_FAILED for resource 660e8500-f29c-41e4-c826-556755550000
Nov 16 11:00:04 mdso-host CIENA[5678]: ResourceAgent: Device validation error DEF-456 on circuit 80.L1XX.006789..CHTR
Nov 16 11:00:05 mdso-host CIENA[5678]: ServiceMapper: DEBUG: Retrying ELINE service configuration
EOF
```

**Expected Extractions:**

| Log Line | circuit_id | error_code | device_fqdn | vendor | orch_state | management_ip | severity |
|----------|-----------|------------|-------------|---------|------------|---------------|----------|
| 1 | 80.L1XX.006789..CHTR | DE-1000 | - | - | - | - | ERROR |
| 2 | - | - | ABCDEFGH01.CHTRSE.COM | adva | - | 10.20.30.40 | FATAL |
| 3 | - | - | - | - | CREATE_FAILED | - | WARN |
| 4 | 80.L1XX.006789..CHTR | DEF-456 | - | - | - | - | INFO |
| 5 | - | - | - | - | - | - | DEBUG |

### Test Log Set 3: Multi-Vendor

```bash
cat > /tmp/test-logs-vendors.txt <<'EOF'
Nov 16 12:00:01 mdso-host CIENA[9999]: ResourceAgent: Provisioning circuit 80.L1XX.001111..CHTR on device CISCO12345.CHTRSE.COM (vendor: cisco)
Nov 16 12:00:02 mdso-host CIENA[9999]: ResourceAgent: Provisioning circuit 80.L1XX.002222..CHTR on device JUNIPER789.CHTRSE.COM (vendor: juniper)
Nov 16 12:00:03 mdso-host CIENA[9999]: ResourceAgent: Provisioning circuit 80.L1XX.003333..CHTR on device ADVADEVICE.CHTRSE.COM (vendor: adva)
Nov 16 12:00:04 mdso-host CIENA[9999]: ResourceAgent: Provisioning circuit 80.L1XX.004444..CHTR on device RADNETWORK.CHTRSE.COM (vendor: rad)
EOF
```

**Expected Extractions:**

All logs should extract:
- Unique circuit_id
- Unique device_fqdn
- Correct vendor (cisco, juniper, adva, rad)
- Correct device_tid (first 10 chars of FQDN)

### Test Log Set 4: Service Types

```bash
cat > /tmp/test-logs-services.txt <<'EOF'
Nov 16 13:00:01 mdso-host CIENA[1111]: ServiceMapper: Configuring service ELAN for circuit 80.L1XX.100001..CHTR
Nov 16 13:00:02 mdso-host CIENA[1111]: ServiceMapper: Configuring service ELINE for circuit 80.L1XX.100002..CHTR
Nov 16 13:00:03 mdso-host CIENA[1111]: ServiceMapper: Configuring service FIA for circuit 80.L1XX.100003..CHTR
Nov 16 13:00:04 mdso-host CIENA[1111]: ServiceMapper: Configuring service VOICE for circuit 80.L1XX.100004..CHTR
Nov 16 13:00:05 mdso-host CIENA[1111]: ServiceMapper: Configuring service VIDEO for circuit 80.L1XX.100005..CHTR
EOF
```

**Expected Extractions:**

All logs should extract:
- service_type (ELAN, ELINE, FIA, VOICE, VIDEO)
- circuit_id
- product_type (service_mapper)

## Test Procedures

### Test 1: Local Regex Validation

Test regex patterns locally before deploying:

```bash
#!/bin/bash
# Save as test-regex.sh

TEST_LOG="Nov 16 10:30:15 mdso-host CIENA[1234]: ServiceMapper: Creating circuit 80.L1XX.005054..CHTR with resource 550e8400-e29b-41d4-a716-446655440000 on device JFVLINBJ2CW.CHTRSE.COM (vendor: juniper)"

echo "Testing Circuit ID extraction:"
echo "$TEST_LOG" | grep -oP '(?i)circuit[:\s]+\K\d+\.\S+'

echo "Testing Resource ID extraction:"
echo "$TEST_LOG" | grep -oP '(?i)resource[:\s]+\K[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

echo "Testing Device FQDN extraction:"
echo "$TEST_LOG" | grep -oP '(?i)(?:device|on)\s+\K[A-Z0-9]{10}\.[A-Z0-9\.]+'

echo "Testing Vendor extraction:"
echo "$TEST_LOG" | grep -oP '(?i)vendor[:\s]+\K(?:juniper|adva|cisco|rad)'

echo "Testing Product Type extraction:"
echo "$TEST_LOG" | grep -oP '(?i)(?:service_mapper|network_service|resource_agent|orchestration_engine)'
```

Run the test:
```bash
chmod +x test-regex.sh
./test-regex.sh
```

**Expected Output:**
```
Testing Circuit ID extraction:
80.L1XX.005054..CHTR
Testing Resource ID extraction:
550e8400-e29b-41d4-a716-446655440000
Testing Device FQDN extraction:
JFVLINBJ2CW.CHTRSE.COM
Testing Vendor extraction:
juniper
Testing Product Type extraction:
service_mapper
```

### Test 2: Inject Sample Logs

Inject test logs into the actual log file:

```bash
# On MDSO server
# Create backup first
sudo cp /var/log/ciena/blueplanet.log /var/log/ciena/blueplanet.log.backup

# Append test logs
cat /tmp/test-logs.txt | sudo tee -a /var/log/ciena/blueplanet.log

# Wait 10-15 seconds for processing
sleep 15

# Check Alloy logs for processing
docker logs --tail 20 alloy-mdso | grep -i "circuit\|resource\|vendor"
```

### Test 3: Verify in Loki

Query Loki to confirm field extraction:

```bash
#!/bin/bash
# Save as verify-loki.sh

LOKI_URL="http://159.56.4.94:3100"

echo "=== Test 1: Query logs with circuit_id ==="
curl -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode 'query={service="mdso", circuit_id!=""}' \
  --data-urlencode 'limit=5' | jq '.data.result[].stream'

echo ""
echo "=== Test 2: Query logs with vendor ==="
curl -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode 'query={service="mdso", vendor!=""}' \
  --data-urlencode 'limit=5' | jq '.data.result[].stream'

echo ""
echo "=== Test 3: Query logs with error codes ==="
curl -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode 'query={service="mdso", error_code!=""}' \
  --data-urlencode 'limit=5' | jq '.data.result[].stream'

echo ""
echo "=== Test 4: Query logs with severity ==="
curl -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode 'query={service="mdso", severity="ERROR"}' \
  --data-urlencode 'limit=5' | jq '.data.result[].stream'
```

Run verification:
```bash
chmod +x verify-loki.sh
./verify-loki.sh
```

**Expected Output:**
Each query should return logs with the corresponding fields populated.

### Test 4: Grafana Visual Validation

1. Open Grafana: `http://159.56.4.94:8443`
2. Navigate to **Explore**
3. Select **Loki** data source
4. Run query: `{service="mdso"}`
5. Click on a log entry to expand
6. Verify **Detected fields** section shows:
   - circuit_id
   - resource_id
   - device_fqdn
   - device_tid
   - vendor
   - orch_state
   - service_type
   - product_type
   - error_code
   - severity

### Test 5: Correlation Engine Validation

Check if correlation engine receives and uses structured fields:

```bash
# On Meta server
# Check correlation engine logs for field usage
docker-compose logs correlation-engine | grep -E "circuit_id|resource_id" | tail -20

# Check correlation metrics
curl http://159.56.4.94:8080/metrics | grep "correlation_score"

# Query correlation API for recent correlations
curl http://159.56.4.94:8080/api/v1/correlations?limit=10 | jq
```

### Test 6: Field Coverage Analysis

Create a script to analyze field extraction coverage:

```bash
#!/bin/bash
# Save as analyze-coverage.sh

LOKI_URL="http://159.56.4.94:3100"
SERVICE="mdso"

echo "=== Field Extraction Coverage Analysis ==="
echo ""

# Total logs
TOTAL=$(curl -s -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode "query=count_over_time({service=\"${SERVICE}\"}[1h])" | \
  jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")

echo "Total logs (last hour): $TOTAL"
echo ""

# Circuit ID coverage
CIRCUIT=$(curl -s -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode "query=count_over_time({service=\"${SERVICE}\", circuit_id!=\"\"}[1h])" | \
  jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
echo "Logs with circuit_id: $CIRCUIT ($(awk "BEGIN {printf \"%.1f\", ($CIRCUIT/$TOTAL)*100}")%)"

# Resource ID coverage
RESOURCE=$(curl -s -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode "query=count_over_time({service=\"${SERVICE}\", resource_id!=\"\"}[1h])" | \
  jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
echo "Logs with resource_id: $RESOURCE ($(awk "BEGIN {printf \"%.1f\", ($RESOURCE/$TOTAL)*100}")%)"

# Vendor coverage
VENDOR=$(curl -s -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode "query=count_over_time({service=\"${SERVICE}\", vendor!=\"\"}[1h])" | \
  jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
echo "Logs with vendor: $VENDOR ($(awk "BEGIN {printf \"%.1f\", ($VENDOR/$TOTAL)*100}")%)"

# Severity coverage
SEVERITY=$(curl -s -G "${LOKI_URL}/loki/api/v1/query" \
  --data-urlencode "query=count_over_time({service=\"${SERVICE}\", severity!=\"\"}[1h])" | \
  jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
echo "Logs with severity: $SEVERITY ($(awk "BEGIN {printf \"%.1f\", ($SEVERITY/$TOTAL)*100}")%)"

echo ""
echo "=== Vendor Breakdown ==="
for vendor in juniper adva cisco rad; do
  COUNT=$(curl -s -G "${LOKI_URL}/loki/api/v1/query" \
    --data-urlencode "query=count_over_time({service=\"${SERVICE}\", vendor=\"${vendor}\"}[1h])" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
  echo "$vendor: $COUNT logs"
done
```

### Test 7: Performance Testing

Test performance with high log volume:

```bash
#!/bin/bash
# Save as performance-test.sh

LOG_FILE="/var/log/ciena/blueplanet.log"
LOG_COUNT=1000

echo "Generating $LOG_COUNT test logs..."
for i in $(seq 1 $LOG_COUNT); do
  echo "$(date '+%b %d %H:%M:%S') mdso-host CIENA[$i]: ServiceMapper: Creating circuit 80.L1XX.$(printf '%06d' $i)..CHTR with resource $(uuidgen)" | sudo tee -a $LOG_FILE > /dev/null
done

echo "Monitoring Alloy performance..."
docker stats --no-stream alloy-mdso

echo "Checking processing lag..."
sleep 30
docker logs --tail 50 alloy-mdso | grep -i "export\|send"
```

**Expected Results:**
- CPU usage < 50%
- Memory usage < 512MB
- No export errors
- Processing lag < 10 seconds

## Validation Checklist

Use this checklist to validate the deployment:

### Basic Functionality
- [ ] Alloy container running
- [ ] Log files accessible to container
- [ ] Logs being tailed successfully
- [ ] Exports to Meta server working

### Field Extraction - Business Identifiers
- [ ] circuit_id extracted from circuit creation logs
- [ ] resource_id extracted (UUID format)
- [ ] product_id extracted (UUID format)

### Field Extraction - Device Context
- [ ] device_fqdn extracted correctly
- [ ] device_tid extracted (10 chars from FQDN)
- [ ] vendor detected (juniper, adva, cisco, rad)
- [ ] management_ip extracted when present

### Field Extraction - Operational Context
- [ ] orch_state extracted (CREATE_IN_PROGRESS, etc.)
- [ ] service_type extracted (ELAN, ELINE, etc.)
- [ ] product_type extracted (service_mapper, etc.)

### Field Extraction - Error Handling
- [ ] error_code extracted (DE-1000, DEF-123, etc.)
- [ ] severity normalized correctly (ERROR, WARN, INFO, etc.)

### Integration Testing
- [ ] Fields visible in Loki
- [ ] Fields visible in Grafana
- [ ] Correlation engine receiving fields
- [ ] Circuit correlation working (+100 score)

### Performance
- [ ] CPU usage acceptable
- [ ] Memory usage acceptable
- [ ] No processing lag
- [ ] No export errors

## Common Issues and Solutions

### Issue: Fields Not Being Extracted

**Diagnosis:**
```bash
# Check if regex patterns match
docker logs alloy-mdso | grep -i "stage\|regex"

# Test with known log format
echo "YOUR_LOG_LINE" | grep -oP 'circuit[:\s]+\K\d+\.\S+'
```

**Solution:**
- Verify log format matches regex patterns
- Adjust regex in config.alloy
- Check for case sensitivity issues
- Verify regex escaping in Alloy syntax

### Issue: Some Logs Have Fields, Others Don't

**Diagnosis:**
```bash
# Get sample of logs without circuit_id
curl -G 'http://159.56.4.94:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso", circuit_id=""}' \
  --data-urlencode 'limit=10' | jq '.data.result[].values[]'
```

**Solution:**
- Normal behavior - not all logs contain all fields
- Document which log types should have which fields
- Adjust regex patterns for specific log formats

### Issue: Wrong Field Values

**Diagnosis:**
```bash
# Check extracted values
curl -G 'http://159.56.4.94:3100/loki/api/v1/label/circuit_id/values'
```

**Solution:**
- Review regex patterns for over-matching
- Add more specific context to regex
- Test with actual log samples

### Issue: Performance Degradation

**Diagnosis:**
```bash
# Check resource usage
docker stats alloy-mdso

# Check processing backlog
docker logs --tail 100 alloy-mdso | grep -i "queue\|buffer"
```

**Solution:**
- Reduce number of regex stages
- Optimize regex patterns
- Increase container resources
- Add batching configuration

## Test Report Template

After testing, document results:

```markdown
# Alloy Enhanced Config Test Report

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Environment:** MDSO Dev (159.56.4.37) → Meta (159.56.4.94)

## Test Summary
- Total test logs: XXX
- Successful extractions: XXX
- Failed extractions: XXX
- Success rate: XX%

## Field Extraction Results
- circuit_id: XX% coverage
- resource_id: XX% coverage
- vendor: XX% coverage
- severity: XX% coverage

## Performance Metrics
- CPU usage: XX%
- Memory usage: XXXMB
- Processing lag: XX seconds
- Export success rate: XX%

## Issues Found
1. [Issue description]
2. [Issue description]

## Recommendations
1. [Recommendation]
2. [Recommendation]

## Approval
- [ ] Ready for production
- [ ] Needs adjustments (see issues)
```

## Next Steps

After successful testing:
1. Update patterns based on real log analysis
2. Add more test cases for edge cases
3. Set up automated testing
4. Configure monitoring alerts
5. Document field extraction coverage expectations
6. Train team on validation procedures

## Automated Testing (Future)

Consider creating automated tests:

```bash
#!/bin/bash
# automated-test.sh (future enhancement)

# 1. Deploy test config
# 2. Inject known test logs
# 3. Query Loki for results
# 4. Compare expected vs actual
# 5. Generate pass/fail report
# 6. Clean up test data
```

## Support

For testing assistance:
- Review sample logs in this guide
- Check regex patterns in config.alloy:29-121
- See DEPLOYMENT-GUIDE-ENHANCED.md for deployment help
- Contact platform team for correlation engine issues
