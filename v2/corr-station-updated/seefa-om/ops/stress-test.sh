#!/bin/bash
################################################################################
# Stress Test Script - Load Testing for Observability Stack
# Usage: ./ops/stress-test.sh [--duration SECONDS] [--rps RATE]
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
DURATION=300  # 5 minutes default
RPS=100       # Requests per second
PARALLEL_USERS=10
SERVICES=("beorn" "palantir" "arda")

# Endpoints
BEORN_URL="http://localhost:5001"
PALANTIR_URL="http://localhost:5002"
ARDA_URL="http://localhost:5003"
CORRELATION_URL="http://localhost:8080"
GATEWAY_URL="http://localhost:4318"

# Statistics
TOTAL_REQUESTS=0
SUCCESSFUL_REQUESTS=0
FAILED_REQUESTS=0
START_TIME=0
END_TIME=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_stat() {
    echo -e "${CYAN}[STAT]${NC} $1"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --rps)
                RPS="$2"
                shift 2
                ;;
            --parallel)
                PARALLEL_USERS="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Usage: $0 [--duration SECONDS] [--rps RATE] [--parallel USERS]"
                exit 1
                ;;
        esac
    done
}

# Check if services are running
check_services() {
    log_info "Checking if services are running..."

    local all_up=true

    for service in "${SERVICES[@]}"; do
        local port
        case $service in
            beorn) port=5002 ;;
            palantir) port=5003 ;;
            arda) port=5001 ;;
        esac

        if curl -sf "http://localhost:$port/health" &> /dev/null; then
            log_success "$service is running"
        else
            log_error "$service is not responding"
            all_up=false
        fi
    done

    if ! curl -sf "$CORRELATION_URL/health" &> /dev/null; then
        log_error "Correlation engine is not responding"
        all_up=false
    else
        log_success "Correlation engine is running"
    fi

    if ! $all_up; then
        log_error "Some services are not running. Start them first."
        exit 1
    fi
}

# Generate random circuit/product IDs
random_circuit_id() {
    echo "CKT-$(shuf -i 10000-99999 -n 1)"
}

random_product_id() {
    echo "PROD-$(shuf -i 1000-9999 -n 1)"
}

random_resource_id() {
    echo "RES-$(shuf -i 100-999 -n 1)"
}

# Test Beorn endpoint
test_beorn() {
    local circuit_id=$(random_circuit_id)
    local product_id=$(random_product_id)

    local response=$(curl -s -w "\n%{http_code}" -X POST "$BEORN_URL/api/circuit" \
        -H "Content-Type: application/json" \
        -d "{\"circuit_id\": \"$circuit_id\", \"product_id\": \"$product_id\", \"action\": \"provision\"}" \
        2>/dev/null)

    local http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        echo "success"
    else
        echo "failed"
    fi
}

# Test Palantir endpoint
test_palantir() {
    local resource_id=$(random_resource_id)

    local response=$(curl -s -w "\n%{http_code}" -X GET "$PALANTIR_URL/api/resource/$resource_id" \
        2>/dev/null)

    local http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "404" ]]; then
        echo "success"
    else
        echo "failed"
    fi
}

# Test Arda endpoint
test_arda() {
    local circuit_id=$(random_circuit_id)

    local response=$(curl -s -w "\n%{http_code}" -X GET "$ARDA_URL/api/status/$circuit_id" \
        2>/dev/null)

    local http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]]; then
        echo "success"
    else
        echo "failed"
    fi
}

# Send direct OTLP logs
send_otlp_logs() {
    local timestamp=$(date -u +%s%N)

    local payload=$(cat <<EOF
{
  "resourceLogs": [
    {
      "resource": {
        "attributes": [
          {"key": "service.name", "value": {"stringValue": "stress-test"}},
          {"key": "deployment.environment", "value": {"stringValue": "dev"}}
        ]
      },
      "scopeLogs": [
        {
          "scope": {"name": "stress-test"},
          "logRecords": [
            {
              "timeUnixNano": "$timestamp",
              "severityText": "INFO",
              "body": {"stringValue": "Stress test log message"},
              "attributes": [
                {"key": "test.iteration", "value": {"intValue": "$TOTAL_REQUESTS"}}
              ]
            }
          ]
        }
      ]
    }
  ]
}
EOF
    )

    local response=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/v1/logs" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        2>/dev/null)

    local http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]]; then
        echo "success"
    else
        echo "failed"
    fi
}

# Worker function for parallel execution
worker() {
    local worker_id=$1
    local end_time=$2
    local requests=0
    local successes=0
    local failures=0

    while [[ $(date +%s) -lt $end_time ]]; do
        # Randomly select a service to test
        local rand=$((RANDOM % 4))
        local result

        case $rand in
            0)
                result=$(test_beorn)
                ;;
            1)
                result=$(test_palantir)
                ;;
            2)
                result=$(test_arda)
                ;;
            3)
                result=$(send_otlp_logs)
                ;;
        esac

        ((requests++))

        if [[ "$result" == "success" ]]; then
            ((successes++))
        else
            ((failures++))
        fi

        # Rate limiting
        sleep $(awk "BEGIN {print 1/$RPS}")
    done

    echo "$requests $successes $failures"
}

# Monitor metrics during test
monitor_metrics() {
    local end_time=$1

    while [[ $(date +%s) -lt $end_time ]]; do
        sleep 10

        # Fetch metrics from correlation engine
        if curl -sf "$CORRELATION_URL/metrics" > /tmp/metrics.txt 2>/dev/null; then
            local logs_processed=$(grep "logs_processed_total" /tmp/metrics.txt | awk '{print $2}' || echo "0")
            local traces_processed=$(grep "traces_processed_total" /tmp/metrics.txt | awk '{print $2}' || echo "0")

            log_stat "Logs: $logs_processed | Traces: $traces_processed"
        fi
    done
}

# Run stress test
run_stress_test() {
    log_info "Starting stress test..."
    log_info "Duration: ${DURATION}s | RPS: $RPS | Parallel Users: $PARALLEL_USERS"
    echo ""

    START_TIME=$(date +%s)
    local end_time=$((START_TIME + DURATION))

    # Start monitoring in background
    monitor_metrics $end_time &
    local monitor_pid=$!

    # Launch workers
    local pids=()
    for i in $(seq 1 $PARALLEL_USERS); do
        worker $i $end_time &
        pids+=($!)
    done

    # Wait for all workers to complete
    for pid in "${pids[@]}"; do
        wait $pid
        local result=$(jobs -p | grep $pid || echo "0 0 0")
        read -r req succ fail <<< "$result"
        TOTAL_REQUESTS=$((TOTAL_REQUESTS + req))
        SUCCESSFUL_REQUESTS=$((SUCCESSFUL_REQUESTS + succ))
        FAILED_REQUESTS=$((FAILED_REQUESTS + fail))
    done

    # Stop monitoring
    kill $monitor_pid 2>/dev/null || true
    wait $monitor_pid 2>/dev/null || true

    END_TIME=$(date +%s)
}

# Calculate statistics
calculate_stats() {
    local elapsed=$((END_TIME - START_TIME))
    local actual_rps=$((TOTAL_REQUESTS / elapsed))
    local success_rate=0

    if [[ $TOTAL_REQUESTS -gt 0 ]]; then
        success_rate=$(awk "BEGIN {printf \"%.2f\", ($SUCCESSFUL_REQUESTS / $TOTAL_REQUESTS) * 100}")
    fi

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_success "Stress Test Complete!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Duration:          ${elapsed}s"
    echo "Total Requests:    $TOTAL_REQUESTS"
    echo "Successful:        $SUCCESSFUL_REQUESTS"
    echo "Failed:            $FAILED_REQUESTS"
    echo "Success Rate:      ${success_rate}%"
    echo "Actual RPS:        ${actual_rps}"
    echo "Target RPS:        $RPS"
    echo "Parallel Users:    $PARALLEL_USERS"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Query correlation engine for results
query_correlations() {
    log_info "Querying correlation engine for test results..."

    if curl -sf "$CORRELATION_URL/metrics" > /tmp/final_metrics.txt 2>/dev/null; then
        echo ""
        echo "Correlation Engine Metrics:"
        echo "───────────────────────────────────────────────────────────────"
        grep -E "(logs_processed|traces_processed|correlation_windows)" /tmp/final_metrics.txt || echo "No metrics found"
        echo "───────────────────────────────────────────────────────────────"
    fi
}

# Generate report
generate_report() {
    local report_file="stress-test-$(date +%Y%m%d-%H%M%S).log"

    cat > "$report_file" << EOF
Stress Test Report
==================
Date: $(date)
Duration: $DURATION seconds
Target RPS: $RPS
Parallel Users: $PARALLEL_USERS

Results:
--------
Total Requests: $TOTAL_REQUESTS
Successful: $SUCCESSFUL_REQUESTS
Failed: $FAILED_REQUESTS
Success Rate: $(awk "BEGIN {printf \"%.2f\", ($SUCCESSFUL_REQUESTS / $TOTAL_REQUESTS) * 100}")%
Actual RPS: $((TOTAL_REQUESTS / (END_TIME - START_TIME)))

Services Tested:
----------------
- Beorn (Circuit Management)
- Palantir (Resource Queries)
- Arda (Status Checks)
- Gateway (Direct OTLP)

Notes:
------
- All requests distributed randomly across services
- Includes correlation engine processing
- Metrics captured from /metrics endpoint
EOF

    log_success "Report saved to: $report_file"
}

# Cleanup
cleanup() {
    rm -f /tmp/metrics.txt /tmp/final_metrics.txt
}

# Main execution
main() {
    trap cleanup EXIT

    parse_args "$@"
    check_services
    run_stress_test
    calculate_stats
    query_correlations
    generate_report

    log_success "All done! 🚀"
}

# Run main
main "$@"