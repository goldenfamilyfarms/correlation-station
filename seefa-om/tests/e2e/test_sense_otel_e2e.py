"""
End-to-End Test Harness for Sense OTel Instrumentation
Blueprint Feature 1: Validate complete telemetry pipeline

Tests the full observability stack:
  Sense Apps (ARDA, BEORN, PALANTIR)
    ↓ (OpenTelemetry)
  Correlation Gateway
    ↓
  Correlation Engine
    ↓
  Grafana Stack (Loki, Tempo, Prometheus)

Usage:
    pytest seefa-om/tests/e2e/test_sense_otel_e2e.py -v
"""
import pytest
import requests
import time
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta


# ===== CONFIGURATION =====

# Sense app endpoints (adjust based on deployment)
ARDA_URL = "http://localhost:8000"
BEORN_URL = "http://localhost:8001"
PALANTIR_URL = "http://localhost:8002"

# Correlation Engine/Gateway
CORRELATION_ENGINE_URL = "http://localhost:8080"
CORRELATION_GATEWAY_URL = "http://localhost:8081"

# Grafana stack endpoints
LOKI_URL = "http://localhost:3100"
TEMPO_URL = "http://localhost:3200"
PROMETHEUS_URL = "http://localhost:9090"

# Test data
TEST_CIRCUIT_ID = f"TEST.CIRCUIT.{int(time.time())}..E2E"
TEST_TIMEOUT = 30  # seconds


# ===== HELPER FUNCTIONS =====

def wait_for_telemetry(seconds: int = 10):
    """Wait for telemetry to propagate through the pipeline"""
    print(f"⏳ Waiting {seconds}s for telemetry propagation...")
    time.sleep(seconds)


def query_loki(query: str, start: Optional[datetime] = None) -> Dict:
    """Query Loki for log entries"""
    if not start:
        start = datetime.utcnow() - timedelta(minutes=5)

    params = {
        "query": query,
        "start": int(start.timestamp() * 1e9),  # nanoseconds
        "limit": 100
    }

    try:
        response = requests.get(f"{LOKI_URL}/loki/api/v1/query_range", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Loki query failed: {e}")
        return {"data": {"result": []}}


def query_tempo(trace_id: str) -> Optional[Dict]:
    """Query Tempo for a specific trace"""
    try:
        response = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Tempo query failed: {e}")
        return None


def search_tempo(tags: Dict[str, str]) -> List[Dict]:
    """Search Tempo for traces matching tags"""
    try:
        # Convert tags to TraceQL query
        tag_filters = " && ".join([f'.{k}="{v}"' for k, v in tags.items()])
        traceql_query = f"{{ {tag_filters} }}"

        params = {
            "q": traceql_query,
            "limit": 10
        }

        response = requests.get(f"{TEMPO_URL}/api/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        return data.get("traces", [])
    except Exception as e:
        print(f"❌ Tempo search failed: {e}")
        return []


def query_prometheus(query: str) -> Dict:
    """Query Prometheus for metrics"""
    try:
        params = {"query": query}
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Prometheus query failed: {e}")
        return {"data": {"result": []}}


# ===== TEST FIXTURES =====

@pytest.fixture(scope="session")
def verify_services_up():
    """Verify all services are reachable before running tests"""
    services = {
        "ARDA": ARDA_URL,
        "BEORN": BEORN_URL,
        "PALANTIR": PALANTIR_URL,
        "Correlation Engine": CORRELATION_ENGINE_URL,
        "Loki": LOKI_URL,
        "Tempo": TEMPO_URL,
        "Prometheus": PROMETHEUS_URL
    }

    print("\n" + "="*60)
    print("VERIFYING SERVICES")
    print("="*60)

    all_up = True
    for name, url in services.items():
        try:
            # Try health endpoint first, fallback to root
            health_urls = [f"{url}/health", f"{url}/ready", url]
            reachable = False

            for health_url in health_urls:
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code < 500:
                        reachable = True
                        print(f"✓ {name}: {url} - UP")
                        break
                except:
                    continue

            if not reachable:
                print(f"✗ {name}: {url} - DOWN")
                all_up = False

        except Exception as e:
            print(f"✗ {name}: {url} - ERROR: {e}")
            all_up = False

    print("="*60)

    if not all_up:
        pytest.skip("Not all services are reachable. Please start the stack first.")


# ===== TESTS =====

class TestARDAOTelInstrumentation:
    """Test ARDA OpenTelemetry instrumentation"""

    def test_arda_circuit_creation_generates_trace(self, verify_services_up):
        """Test that ARDA circuit creation generates a complete trace"""
        print("\n" + "="*60)
        print("TEST: ARDA Circuit Creation Trace")
        print("="*60)

        # Step 1: Trigger circuit creation
        circuit_data = {
            "circuit_id": TEST_CIRCUIT_ID,
            "product_type": "eline",
            "bandwidth": "10G",
            "device_a": "router-a.demo.com",
            "device_z": "router-z.demo.com"
        }

        print(f"→ Creating circuit: {TEST_CIRCUIT_ID}")
        response = requests.post(
            f"{ARDA_URL}/api/v1/circuit",
            json=circuit_data,
            timeout=10
        )

        assert response.status_code in [200, 201], f"Circuit creation failed: {response.text}"
        print(f"✓ Circuit created: {response.status_code}")

        # Step 2: Wait for telemetry
        wait_for_telemetry(15)

        # Step 3: Search for trace in Tempo
        print(f"→ Searching Tempo for circuit_id={TEST_CIRCUIT_ID}")
        traces = search_tempo({"circuit_id": TEST_CIRCUIT_ID})

        assert len(traces) > 0, f"No traces found for circuit {TEST_CIRCUIT_ID}"
        print(f"✓ Found {len(traces)} trace(s) in Tempo")

        # Step 4: Verify trace attributes
        trace = traces[0]
        trace_id = trace.get("traceID")

        assert trace_id, "Trace ID not found"
        print(f"✓ Trace ID: {trace_id}")

        # Get full trace details
        full_trace = query_tempo(trace_id)
        assert full_trace, f"Could not retrieve full trace {trace_id}"

        # Verify spans
        batches = full_trace.get("batches", [])
        assert len(batches) > 0, "No span batches found in trace"

        total_spans = sum(len(batch.get("scopeSpans", [])[0].get("spans", [])) for batch in batches if batch.get("scopeSpans"))
        print(f"✓ Trace contains {total_spans} span(s)")

        # Verify key attributes are present
        for batch in batches:
            resource_attrs = batch.get("resource", {}).get("attributes", [])
            attr_dict = {attr["key"]: attr["value"] for attr in resource_attrs}

            if "service.name" in attr_dict:
                service_name = attr_dict["service.name"].get("stringValue", "")
                print(f"  - Service: {service_name}")

        print("="*60)

    def test_arda_logs_correlated_with_traces(self, verify_services_up):
        """Test that ARDA logs are correlated with traces"""
        print("\n" + "="*60)
        print("TEST: ARDA Log-Trace Correlation")
        print("="*60)

        # Query Loki for logs containing our test circuit ID
        logql_query = f'{{job="arda"}} |= "{TEST_CIRCUIT_ID}"'
        print(f"→ Querying Loki: {logql_query}")

        result = query_loki(logql_query)
        log_entries = result.get("data", {}).get("result", [])

        assert len(log_entries) > 0, f"No logs found for circuit {TEST_CIRCUIT_ID}"
        print(f"✓ Found {len(log_entries)} log stream(s)")

        # Check for trace_id in log entries
        has_trace_id = False
        for stream in log_entries:
            for value in stream.get("values", []):
                log_line = value[1] if len(value) > 1 else ""
                if "trace_id" in log_line.lower() or "traceid" in log_line.lower():
                    has_trace_id = True
                    print(f"✓ Log entry contains trace correlation")
                    break
            if has_trace_id:
                break

        assert has_trace_id, "Logs do not contain trace correlation information"
        print("="*60)


class TestBEORNOTelInstrumentation:
    """Test BEORN OpenTelemetry instrumentation"""

    def test_beorn_scriptplan_execution_generates_trace(self, verify_services_up):
        """Test that BEORN MDSO scriptplan execution generates trace"""
        print("\n" + "="*60)
        print("TEST: BEORN ScriptPlan Execution Trace")
        print("="*60)

        # Trigger MDSO scriptplan execution
        scriptplan_data = {
            "plan_name": "provision_eline",
            "circuit_id": TEST_CIRCUIT_ID,
            "device": "ciena-saos-demo.demo.com"
        }

        print(f"→ Executing scriptplan for circuit: {TEST_CIRCUIT_ID}")
        response = requests.post(
            f"{BEORN_URL}/api/v1/scriptplan/execute",
            json=scriptplan_data,
            timeout=10
        )

        assert response.status_code in [200, 201], f"ScriptPlan execution failed: {response.text}"
        print(f"✓ ScriptPlan executed: {response.status_code}")

        # Wait for telemetry
        wait_for_telemetry(15)

        # Search for trace
        print(f"→ Searching Tempo for service.name=beorn")
        traces = search_tempo({"service.name": "beorn"})

        assert len(traces) > 0, "No BEORN traces found in Tempo"
        print(f"✓ Found {len(traces)} BEORN trace(s)")

        print("="*60)


class TestPALANTIRMetrics:
    """Test PALANTIR metrics instrumentation"""

    def test_palantir_request_metrics_recorded(self, verify_services_up):
        """Test that PALANTIR request metrics are recorded in Prometheus"""
        print("\n" + "="*60)
        print("TEST: PALANTIR Request Metrics")
        print("="*60)

        # Trigger some PALANTIR requests
        for i in range(5):
            try:
                response = requests.get(f"{PALANTIR_URL}/api/v1/health", timeout=5)
                print(f"  Request {i+1}/5: {response.status_code}")
            except:
                pass
            time.sleep(0.5)

        # Wait for metrics to be scraped
        wait_for_telemetry(10)

        # Query Prometheus for sense_requests_total metric
        promql_query = 'sense_requests_total{service_name="palantir"}'
        print(f"→ Querying Prometheus: {promql_query}")

        result = query_prometheus(promql_query)
        metrics = result.get("data", {}).get("result", [])

        assert len(metrics) > 0, "No PALANTIR request metrics found in Prometheus"
        print(f"✓ Found {len(metrics)} metric series")

        # Print metric values
        for metric in metrics:
            labels = metric.get("metric", {})
            value = metric.get("value", [None, None])[1]
            print(f"  - {labels}: {value}")

        print("="*60)


class TestMetricsCardinality:
    """Test that metrics follow cardinality safety guidelines"""

    def test_request_counter_has_safe_cardinality(self, verify_services_up):
        """Test that sense_requests_total uses safe labels"""
        print("\n" + "="*60)
        print("TEST: Metrics Cardinality Safety")
        print("="*60)

        # Query for all sense_requests_total metrics
        promql_query = 'sense_requests_total'
        print(f"→ Querying Prometheus: {promql_query}")

        result = query_prometheus(promql_query)
        metrics = result.get("data", {}).get("result", [])

        assert len(metrics) > 0, "No sense_requests_total metrics found"
        print(f"✓ Found {len(metrics)} metric series")

        # Verify labels are safe (low cardinality)
        safe_labels = {"service_name", "endpoint_group", "product_type", "result_type", "job", "instance"}
        unsafe_labels = {"circuit_id", "user_id", "session_id", "request_id"}

        for metric in metrics:
            labels = metric.get("metric", {})
            label_keys = set(labels.keys())

            # Check for unsafe labels
            found_unsafe = label_keys & unsafe_labels
            assert len(found_unsafe) == 0, f"Found unsafe labels: {found_unsafe}"

            print(f"  ✓ Safe labels: {label_keys & safe_labels}")

        print("="*60)


class TestEndToEndTelemetryPipeline:
    """Test complete end-to-end telemetry pipeline"""

    def test_full_pipeline_arda_to_grafana(self, verify_services_up):
        """Test complete telemetry flow from ARDA through to Grafana stack"""
        print("\n" + "="*60)
        print("TEST: Full E2E Telemetry Pipeline")
        print("="*60)

        # Create a unique test ID for this run
        test_id = f"E2E.TEST.{int(time.time())}"

        print(f"→ Test ID: {test_id}")

        # Step 1: Trigger ARDA operation
        circuit_data = {
            "circuit_id": test_id,
            "product_type": "eline",
            "bandwidth": "10G"
        }

        print("→ Step 1: Triggering ARDA operation")
        response = requests.post(
            f"{ARDA_URL}/api/v1/circuit",
            json=circuit_data,
            timeout=10
        )
        assert response.status_code in [200, 201]
        print("  ✓ ARDA operation triggered")

        # Step 2: Wait for telemetry propagation
        wait_for_telemetry(20)

        # Step 3: Verify in Tempo
        print("→ Step 2: Verifying trace in Tempo")
        traces = search_tempo({"circuit_id": test_id})
        assert len(traces) > 0, f"Trace not found in Tempo for {test_id}"
        trace_id = traces[0].get("traceID")
        print(f"  ✓ Trace found in Tempo: {trace_id}")

        # Step 4: Verify in Loki
        print("→ Step 3: Verifying logs in Loki")
        logql_query = f'{{job="arda"}} |= "{test_id}"'
        result = query_loki(logql_query)
        log_entries = result.get("data", {}).get("result", [])
        assert len(log_entries) > 0, f"Logs not found in Loki for {test_id}"
        print(f"  ✓ Logs found in Loki: {len(log_entries)} stream(s)")

        # Step 5: Verify in Prometheus
        print("→ Step 4: Verifying metrics in Prometheus")
        promql_query = 'sense_requests_total{service_name="arda"}'
        result = query_prometheus(promql_query)
        metrics = result.get("data", {}).get("result", [])
        assert len(metrics) > 0, "Metrics not found in Prometheus"
        print(f"  ✓ Metrics found in Prometheus: {len(metrics)} series")

        print("\n" + "="*60)
        print("✅ E2E PIPELINE TEST PASSED")
        print("="*60)
        print(f"Test ID: {test_id}")
        print(f"Trace ID: {trace_id}")
        print(f"Logs: {len(log_entries)} streams")
        print(f"Metrics: {len(metrics)} series")
        print("="*60)


# ===== PYTEST CONFIGURATION =====

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end integration test"
    )


if __name__ == "__main__":
    # Allow running as standalone script
    pytest.main([__file__, "-v", "-s"])
