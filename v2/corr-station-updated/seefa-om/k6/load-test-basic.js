/**
 * k6 Basic Load Test for Correlation Engine
 * Tests basic API endpoints under moderate load
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiDuration = new Trend('api_duration');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp up to 20 users
    { duration: '1m', target: 20 },   // Stay at 20 users
    { duration: '30s', target: 50 },  // Ramp up to 50 users
    { duration: '1m', target: 50 },   // Stay at 50 users
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
    http_req_failed: ['rate<0.1'],    // Error rate should be less than 10%
    errors: ['rate<0.1'],              // Custom error rate should be less than 10%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://correlation-engine:8080';

export default function () {
  // Test 1: Health check
  let response = http.get(`${BASE_URL}/health`);
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check has status field': (r) => JSON.parse(r.body).status !== undefined,
  }) || errorRate.add(1);
  apiDuration.add(response.timings.duration);

  sleep(1);

  // Test 2: Root endpoint
  response = http.get(`${BASE_URL}/`);
  check(response, {
    'root endpoint status is 200': (r) => r.status === 200,
    'root endpoint has service field': (r) => JSON.parse(r.body).service === 'correlation-engine',
  }) || errorRate.add(1);
  apiDuration.add(response.timings.duration);

  sleep(1);

  // Test 3: Metrics endpoint
  response = http.get(`${BASE_URL}/metrics`);
  check(response, {
    'metrics endpoint status is 200': (r) => r.status === 200,
    'metrics endpoint returns prometheus format': (r) => r.body.includes('# HELP'),
  }) || errorRate.add(1);
  apiDuration.add(response.timings.duration);

  sleep(1);

  // Test 4: Query correlations (GET)
  response = http.get(`${BASE_URL}/api/correlations?limit=10`);
  check(response, {
    'correlations query status is 200': (r) => r.status === 200,
    'correlations query returns array': (r) => Array.isArray(JSON.parse(r.body).correlations),
  }) || errorRate.add(1);
  apiDuration.add(response.timings.duration);

  sleep(2);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;

  let summary = `
${indent}Test Summary
${indent}============
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
${indent}  Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
${indent}  API Duration (avg): ${data.metrics.api_duration.values.avg.toFixed(2)}ms
`;

  return summary;
}
