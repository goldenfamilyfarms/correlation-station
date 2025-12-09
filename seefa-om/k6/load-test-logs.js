/**
 * k6 Load Test for Log Ingestion
 * Tests log ingestion endpoints with realistic payloads
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const logsIngested = new Counter('logs_ingested');
const ingestionDuration = new Trend('ingestion_duration');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 users
    { duration: '2m', target: 10 },   // Stay at 10 users
    { duration: '30s', target: 30 },  // Ramp up to 30 users
    { duration: '2m', target: 30 },   // Stay at 30 users
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.05'],
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://correlation-engine:8080';

// Generate trace ID
function generateTraceId() {
  return Array.from({ length: 32 }, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
}

// Generate span ID
function generateSpanId() {
  return Array.from({ length: 16 }, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
}

export default function () {
  const traceId = generateTraceId();
  const spanId = generateSpanId();
  const timestamp = new Date().toISOString();

  // Create realistic log payload
  const logPayload = {
    logs: [
      {
        timestamp: timestamp,
        level: 'info',
        message: 'User login successful',
        service: 'auth-service',
        trace_id: traceId,
        span_id: spanId,
        attributes: {
          user_id: `user_${Math.floor(Math.random() * 10000)}`,
          ip_address: `192.168.1.${Math.floor(Math.random() * 255)}`,
          method: 'POST',
          endpoint: '/api/auth/login',
          duration_ms: Math.floor(Math.random() * 200),
        },
      },
      {
        timestamp: new Date(Date.now() + 100).toISOString(),
        level: 'debug',
        message: 'Database query executed',
        service: 'auth-service',
        trace_id: traceId,
        span_id: spanId,
        attributes: {
          query: 'SELECT * FROM users WHERE id = ?',
          duration_ms: Math.floor(Math.random() * 50),
          rows_returned: 1,
        },
      },
      {
        timestamp: new Date(Date.now() + 200).toISOString(),
        level: Math.random() > 0.9 ? 'error' : 'info',
        message: Math.random() > 0.9 ? 'Failed to authenticate user' : 'Session created',
        service: 'auth-service',
        trace_id: traceId,
        span_id: spanId,
        attributes: {
          session_id: `sess_${Math.floor(Math.random() * 100000)}`,
          ttl_seconds: 3600,
        },
      },
    ],
  };

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  // Send log batch
  const response = http.post(
    `${BASE_URL}/api/logs`,
    JSON.stringify(logPayload),
    params
  );

  const success = check(response, {
    'log ingestion status is 200': (r) => r.status === 200,
    'log ingestion response has accepted field': (r) => {
      try {
        return JSON.parse(r.body).accepted !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (success) {
    logsIngested.add(logPayload.logs.length);
  } else {
    errorRate.add(1);
  }

  ingestionDuration.add(response.timings.duration);

  sleep(Math.random() * 2 + 1); // Sleep 1-3 seconds
}

export function handleSummary(data) {
  return {
    'logs-summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';

  let summary = `
${indent}Log Ingestion Load Test Summary
${indent}================================
${indent}
${indent}Duration: ${data.state.testRunDurationMs / 1000}s
${indent}VUs: ${data.metrics.vus.values.max}
${indent}Iterations: ${data.metrics.iterations.values.count}
${indent}
${indent}HTTP Metrics:
${indent}  Requests: ${data.metrics.http_reqs.values.count}
${indent}  Duration (avg): ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
${indent}  Duration (p95): ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
${indent}  Duration (p99): ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
${indent}  Failed: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
${indent}
${indent}Custom Metrics:
${indent}  Logs Ingested: ${data.metrics.logs_ingested.values.count}
${indent}  Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
${indent}  Ingestion Duration (avg): ${data.metrics.ingestion_duration.values.avg.toFixed(2)}ms
${indent}  Ingestion Duration (p95): ${data.metrics.ingestion_duration.values['p(95)'].toFixed(2)}ms
`;

  return summary;
}
