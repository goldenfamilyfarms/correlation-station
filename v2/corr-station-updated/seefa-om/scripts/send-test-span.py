#!/usr/bin/env python3
"""
Send test telemetry (traces, logs, metrics) to OTel Collector
"""
import time
import json
import requests
from datetime import datetime

OTLP_ENDPOINT = "http://localhost:55681/v1/traces"
CORRELATION_ENDPOINT = "http://localhost:8080/ingest"
AUTH_TOKEN = "dev-secret-token-change-me"


def generate_trace_id():
    """Generate a random 32-character hex trace ID"""
    import secrets
    return secrets.token_hex(16)


def generate_span_id():
    """Generate a random 16-character hex span ID"""
    import secrets
    return secrets.token_hex(8)


def send_test_trace():
    """Send a test trace with multiple spans"""
    trace_id = generate_trace_id()
    root_span_id = generate_span_id()
    child_span_id = generate_span_id()

    now_ns = int(time.time() * 1e9)

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "test-service"}},
                        {"key": "deployment.environment", "value": {"stringValue": "dev"}},
                        {"key": "test.source", "value": {"stringValue": "send-test-span.py"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "test-instrumentation",
                            "version": "1.0.0"
                        },
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": root_span_id,
                                "name": "test.root_operation",
                                "kind": 1,
                                "startTimeUnixNano": now_ns - 100_000_000,
                                "endTimeUnixNano": now_ns,
                                "attributes": [
                                    {"key": "http.method", "value": {"stringValue": "POST"}},
                                    {"key": "http.status_code", "value": {"intValue": 200}},
                                    {"key": "test.type", "value": {"stringValue": "synthetic"}}
                                ],
                                "status": {"code": 1}
                            },
                            {
                                "traceId": trace_id,
                                "spanId": child_span_id,
                                "parentSpanId": root_span_id,
                                "name": "test.child_operation",
                                "kind": 3,
                                "startTimeUnixNano": now_ns - 80_000_000,
                                "endTimeUnixNano": now_ns - 20_000_000,
                                "attributes": [
                                    {"key": "db.system", "value": {"stringValue": "postgresql"}},
                                    {"key": "db.statement", "value": {"stringValue": "SELECT * FROM test"}}
                                ],
                                "status": {"code": 1}
                            }
                        ]
                    }
                ]
            }
        ]
    }

    try:
        print(f"Sending test trace (trace_id={trace_id})...")
        response = requests.post(
            OTLP_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        print(f"✓ Trace sent successfully to OTLP endpoint")
        return trace_id
    except Exception as e:
        print(f"✗ Failed to send trace: {e}")
        return None


def send_test_log(trace_id):
    """Send a test log correlated with the trace"""
    now_ns = int(time.time() * 1e9)
    span_id = generate_span_id()

    payload = {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "test-service"}},
                        {"key": "deployment.environment", "value": {"stringValue": "dev"}}
                    ]
                },
                "scopeLogs": [
                    {
                        "scope": {
                            "name": "test-logger",
                            "version": "1.0.0"
                        },
                        "logRecords": [
                            {
                                "timeUnixNano": now_ns,
                                "severityNumber": 9,
                                "severityText": "INFO",
                                "body": {
                                    "stringValue": "This is a test log message correlated with trace"
                                },
                                "attributes": [
                                    {"key": "trace_id", "value": {"stringValue": trace_id}},
                                    {"key": "span_id", "value": {"stringValue": span_id}},
                                    {"key": "log.source", "value": {"stringValue": "test-script"}}
                                ],
                                "traceId": trace_id,
                                "spanId": span_id
                            }
                        ]
                    }
                ]
            }
        ]
    }

    try:
        print(f"Sending test log (trace_id={trace_id})...")
        response = requests.post(
            "http://localhost:55681/v1/logs",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        print(f"✓ Log sent successfully")
    except Exception as e:
        print(f"✗ Failed to send log: {e}")


def send_to_correlation_api(trace_id):
    """Send test data directly to Correlation API"""
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "test-direct"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": generate_span_id(),
                                "name": "direct.correlation.test",
                                "startTimeUnixNano": int(time.time() * 1e9) - 50_000_000,
                                "endTimeUnixNano": int(time.time() * 1e9)
                            }
                        ]
                    }
                ]
            }
        ]
    }

    try:
        print(f"Sending to Correlation API...")
        response = requests.post(
            CORRELATION_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            timeout=5
        )
        response.raise_for_status()
        print(f"✓ Sent to Correlation API: {response.json()}")
    except Exception as e:
        print(f"✗ Failed to send to Correlation API: {e}")


def main():
    print("=" * 50)
    print("Sending Test Telemetry")
    print("=" * 50)
    print()

    # Send test trace
    trace_id = send_test_trace()

    if trace_id:
        time.sleep(0.5)

        # Send correlated log
        send_test_log(trace_id)

        time.sleep(0.5)

        # Send to Correlation API
        send_to_correlation_api(trace_id)

        print()
        print("=" * 50)
        print(f"✓ Test complete!")
        print(f"  Trace ID: {trace_id}")
        print(f"  View in Grafana: http://159.56.4.94:3000")
        print(f"  Search in Tempo for trace: {trace_id}")
        print("=" * 50)
    else:
        print("\n✗ Test failed")


if __name__ == "__main__":
    main()