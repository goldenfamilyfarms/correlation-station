import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { BookOpen, Code, Zap, Database } from 'lucide-react'

export default function DocumentationPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Documentation</h1>
        <p className="text-lg text-gray-600">
          Comprehensive guides for mastering observability tools and practices
        </p>
      </div>

      <Tabs defaultValue="traceql" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="traceql">TraceQL</TabsTrigger>
          <TabsTrigger value="promql">PromQL</TabsTrigger>
          <TabsTrigger value="logql">LogQL</TabsTrigger>
          <TabsTrigger value="instrumentation">Instrumentation</TabsTrigger>
          <TabsTrigger value="opentelemetry">OpenTelemetry SDK</TabsTrigger>
        </TabsList>

        {/* TraceQL Tab */}
        <TabsContent value="traceql" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-grafana-orange" />
                <CardTitle>TraceQL - Trace Query Language</CardTitle>
              </div>
              <CardDescription>
                Query and analyze distributed traces in Grafana Tempo
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-2">What is TraceQL?</h3>
                <p className="text-gray-600 mb-4">
                  TraceQL is a query language designed for selecting traces in Grafana Tempo.
                  It allows you to filter traces based on span attributes, duration, errors, and more.
                </p>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Basic Syntax</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Find all traces for a specific service</div>
                    <div>{'{ .service.name = "auth-service" }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Find traces with errors</div>
                    <div>{'{ status = error }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Find slow traces (duration {'>'} 1s)</div>
                    <div>{'{ duration > 1s }'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Advanced Queries</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Combine multiple conditions</div>
                    <div>{'{ .service.name = "api-gateway" && status = error && duration > 500ms }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Filter by resource attributes</div>
                    <div>{'{ resource.deployment.environment = "production" && .http.status_code >= 500 }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Search for specific span names</div>
                    <div>{'{ name = "database-query" && duration > 100ms }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Aggregate functions</div>
                    <div>{'{ .service.name = "payment-service" } | rate() by (.http.method)'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Common Selectors</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">.service.name</code>
                    <p className="text-sm text-gray-600 mt-1">Service name attribute</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">status</code>
                    <p className="text-sm text-gray-600 mt-1">Span status (ok, error, unset)</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">duration</code>
                    <p className="text-sm text-gray-600 mt-1">Span duration</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">.http.status_code</code>
                    <p className="text-sm text-gray-600 mt-1">HTTP response status</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">name</code>
                    <p className="text-sm text-gray-600 mt-1">Span name</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">resource.*</code>
                    <p className="text-sm text-gray-600 mt-1">Resource-level attributes</p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Pro Tips</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-600">
                  <li>Use <code className="bg-gray-100 px-2 py-1 rounded">&&</code> for AND conditions, <code className="bg-gray-100 px-2 py-1 rounded">||</code> for OR</li>
                  <li>Duration units: <code className="bg-gray-100 px-2 py-1 rounded">ms</code>, <code className="bg-gray-100 px-2 py-1 rounded">s</code>, <code className="bg-gray-100 px-2 py-1 rounded">m</code>, <code className="bg-gray-100 px-2 py-1 rounded">h</code></li>
                  <li>Use regex with <code className="bg-gray-100 px-2 py-1 rounded">=~</code> operator: <code className="bg-gray-100 px-2 py-1 rounded">{'{ .service.name =~ ".*-service" }'}</code></li>
                  <li>Trace-level queries use <code className="bg-gray-100 px-2 py-1 rounded">{'{}'}</code>, span-level use <code className="bg-gray-100 px-2 py-1 rounded">span</code> selector</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* PromQL Tab */}
        <TabsContent value="promql" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-grafana-orange" />
                <CardTitle>PromQL - Prometheus Query Language</CardTitle>
              </div>
              <CardDescription>
                Query and aggregate metrics in Prometheus and Grafana
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-2">What is PromQL?</h3>
                <p className="text-gray-600 mb-4">
                  PromQL is a functional query language that allows you to select, aggregate, and analyze
                  time series data collected in Prometheus.
                </p>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Basic Queries</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Get current value of a metric</div>
                    <div>http_requests_total</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Filter by labels</div>
                    <div>{'http_requests_total{method="GET", status="200"}'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Rate of requests over 5 minutes</div>
                    <div>rate(http_requests_total[5m])</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Aggregation Functions</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Sum requests across all services</div>
                    <div>{'sum(rate(http_requests_total[5m]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Average CPU usage by service</div>
                    <div>{'avg by (service) (cpu_usage_percent)'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// 95th percentile latency</div>
                    <div>{'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Count of unique services</div>
                    <div>{'count(count by (service) (up))'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Common Functions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">rate()</code>
                    <p className="text-sm text-gray-600 mt-1">Per-second rate over time range</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">irate()</code>
                    <p className="text-sm text-gray-600 mt-1">Instant rate (last 2 points)</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">increase()</code>
                    <p className="text-sm text-gray-600 mt-1">Total increase over time range</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">sum()</code>
                    <p className="text-sm text-gray-600 mt-1">Sum values across series</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">avg()</code>
                    <p className="text-sm text-gray-600 mt-1">Average values across series</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">max()/min()</code>
                    <p className="text-sm text-gray-600 mt-1">Maximum/minimum values</p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Advanced Examples</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Error rate percentage</div>
                    <div>{'100 * sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Top 5 services by request rate</div>
                    <div>{'topk(5, sum by (service) (rate(http_requests_total[5m])))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Alert if service is down</div>
                    <div>{'up{job="api-server"} == 0'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Pro Tips</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-600">
                  <li>Always use <code className="bg-gray-100 px-2 py-1 rounded">rate()</code> with counters, never raw counter values</li>
                  <li>Use <code className="bg-gray-100 px-2 py-1 rounded">by (label)</code> to preserve labels in aggregations</li>
                  <li>Range selectors like <code className="bg-gray-100 px-2 py-1 rounded">[5m]</code> must be at least 2x scrape interval</li>
                  <li>Regex matching: <code className="bg-gray-100 px-2 py-1 rounded">=~</code> for match, <code className="bg-gray-100 px-2 py-1 rounded">!~</code> for not match</li>
                  <li>Use <code className="bg-gray-100 px-2 py-1 rounded">offset</code> to compare with past: <code className="bg-gray-100 px-2 py-1 rounded">metric offset 1h</code></li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* LogQL Tab */}
        <TabsContent value="logql" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-grafana-orange" />
                <CardTitle>LogQL - Log Query Language</CardTitle>
              </div>
              <CardDescription>
                Query and analyze logs in Grafana Loki
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-2">What is LogQL?</h3>
                <p className="text-gray-600 mb-4">
                  LogQL is Grafana Loki's query language, inspired by PromQL. It allows you to query,
                  filter, and aggregate log data using label selectors and line filters.
                </p>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Basic Syntax</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Get logs for a specific service</div>
                    <div>{'{ service_name="auth-service" }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Filter logs containing "error"</div>
                    <div>{'{ service_name="api" } |= "error"'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
                    <div className="text-grafana-orange">// Exclude logs containing "debug"</div>
                    <div>{'{ job="app" } != "debug"'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Log Stream Selectors</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Multiple label matchers</div>
                    <div>{'{ service_name="api", environment="production", level="error" }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Regex matching</div>
                    <div>{'{ service_name=~"api.*", level!~"debug|trace" }'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Using or operator (|)</div>
                    <div>{'{ service_name="api" } | { service_name="gateway" }'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Line Filter Operators</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">|=</code>
                    <p className="text-sm text-gray-600 mt-1">Line contains string (case-sensitive)</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">!=</code>
                    <p className="text-sm text-gray-600 mt-1">Line does not contain string</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">|~</code>
                    <p className="text-sm text-gray-600 mt-1">Line matches regex</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-blue">!~</code>
                    <p className="text-sm text-gray-600 mt-1">Line does not match regex</p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Parser Expressions</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Parse JSON logs</div>
                    <div>{'{ service_name="api" } | json'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Parse specific JSON fields</div>
                    <div>{'{ job="app" } | json level, message, user_id'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Parse logfmt format</div>
                    <div>{'{ service_name="gateway" } | logfmt'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Parse with regex and extract labels</div>
                    <div>{'{ job="nginx" } | regexp `(?P<ip>\\S+) - (?P<user>\\S+) \\[(?P<timestamp>[^]]+)\\]`'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Label Filter Expressions</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Filter after parsing</div>
                    <div>{'{ job="app" } | json | level="error" and status_code >= 500'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Using comparison operators</div>
                    <div>{'{ service_name="api" } | json | duration > 1000 and user_id != ""'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Aggregation Functions</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Count logs per second by service</div>
                    <div>{'sum by (service_name) (rate({ job="app" }[5m]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Count error logs</div>
                    <div>{'sum(count_over_time({ service_name="api" } |= "error" [5m]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Calculate bytes processed</div>
                    <div>{'sum(bytes_over_time({ job="nginx" }[1h]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Average of extracted values</div>
                    <div>{'avg_over_time({ job="api" } | json | unwrap duration [5m])'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Common Aggregation Functions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">rate()</code>
                    <p className="text-sm text-gray-600 mt-1">Calculate per-second rate</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">count_over_time()</code>
                    <p className="text-sm text-gray-600 mt-1">Count log lines</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">bytes_over_time()</code>
                    <p className="text-sm text-gray-600 mt-1">Sum log bytes</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">sum()</code>
                    <p className="text-sm text-gray-600 mt-1">Sum values across series</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">avg()</code>
                    <p className="text-sm text-gray-600 mt-1">Average values</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <code className="font-semibold text-grafana-green">max()/min()</code>
                    <p className="text-sm text-gray-600 mt-1">Maximum/minimum values</p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Advanced Examples</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Error rate by service</div>
                    <div>{'sum by (service_name) (rate({ level="error" }[5m]))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Top 10 error messages</div>
                    <div>{'topk(10, sum by (message) (count_over_time({ level="error" } | json [1h])))'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// 95th percentile response time</div>
                    <div>{'quantile_over_time(0.95, { job="api" } | json | unwrap duration [5m])'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Logs per minute with formatting</div>
                    <div>{'{ service_name="api" } | json | line_format "{{.timestamp}} [{{.level}}] {{.message}}"'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Unwrap for Metrics Extraction</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Extract and aggregate numeric values</div>
                    <div>{'sum_over_time({ job="api" } | json | unwrap bytes_sent [5m])'}</div>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Convert duration labels to metrics</div>
                    <div>{'avg_over_time({ service_name="payment" } | json | unwrap request_duration_ms [10m])'}</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Pro Tips</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-600">
                  <li>Use label selectors first for efficient queries - they leverage Loki's index</li>
                  <li>Chain filters for better performance: <code className="bg-gray-100 px-2 py-1 rounded">{'{ } |= "error" |= "timeout"'}</code></li>
                  <li>Use <code className="bg-gray-100 px-2 py-1 rounded">| json</code> to parse structured logs and filter on fields</li>
                  <li>Keep label cardinality low - use line filters for high-cardinality data</li>
                  <li>Use <code className="bg-gray-100 px-2 py-1 rounded">unwrap</code> to extract metrics from logs for aggregation</li>
                  <li>Combine with <code className="bg-gray-100 px-2 py-1 rounded">line_format</code> to customize log output</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Instrumentation Tab */}
        <TabsContent value="instrumentation" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Code className="h-5 w-5 text-grafana-orange" />
                <CardTitle>Application Instrumentation</CardTitle>
              </div>
              <CardDescription>
                Learn how to instrument your applications for observability
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-2">Why Instrument?</h3>
                <p className="text-gray-600 mb-4">
                  Instrumentation adds observability to your code by emitting logs, metrics, and traces.
                  This data helps you understand system behavior, debug issues, and monitor performance.
                </p>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Python (FastAPI) Example</h3>
                <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                  <pre>{`from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI

# Create tracer
tracer = trace.get_tracer(__name__)

app = FastAPI()

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    # Create custom span
    with tracer.start_as_current_span("fetch_user_from_db") as span:
        span.set_attribute("user.id", user_id)
        # Your database query here
        user = await db.get_user(user_id)
        span.set_attribute("user.email", user.email)
        return user`}</pre>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Key Instrumentation Concepts</h3>
                <div className="space-y-4">
                  <div className="border-l-4 border-grafana-orange pl-4">
                    <h4 className="font-semibold mb-1">Spans</h4>
                    <p className="text-sm text-gray-600">
                      Represent a unit of work. Add custom spans for important operations like database queries or external API calls.
                    </p>
                  </div>
                  <div className="border-l-4 border-grafana-blue pl-4">
                    <h4 className="font-semibold mb-1">Attributes</h4>
                    <p className="text-sm text-gray-600">
                      Key-value pairs that add context to spans. Include user IDs, operation types, error messages, etc.
                    </p>
                  </div>
                  <div className="border-l-4 border-grafana-green pl-4">
                    <h4 className="font-semibold mb-1">Context Propagation</h4>
                    <p className="text-sm text-gray-600">
                      Pass trace context between services using W3C Trace Context headers (traceparent, tracestate).
                    </p>
                  </div>
                  <div className="border-l-4 border-grafana-yellow pl-4">
                    <h4 className="font-semibold mb-1">Semantic Conventions</h4>
                    <p className="text-sm text-gray-600">
                      Use standard attribute names (http.method, db.system, etc.) for consistency across services.
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Best Practices</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-600">
                  <li>✅ Use auto-instrumentation libraries when available (FastAPI, Flask, Express, etc.)</li>
                  <li>✅ Add custom spans for business-critical operations</li>
                  <li>✅ Include meaningful attributes (user_id, operation_type, error_code)</li>
                  <li>✅ Use structured logging with correlation IDs</li>
                  <li>❌ Don't add PII (passwords, SSNs) to span attributes</li>
                  <li>❌ Don't create too many spans (keep cardinality reasonable)</li>
                  <li>❌ Don't forget to handle errors and set span status</li>
                </ul>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Common Patterns</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Error handling</div>
                    <pre>{`try:
    result = await risky_operation()
except Exception as e:
    span.set_status(Status(StatusCode.ERROR))
    span.record_exception(e)
    raise`}</pre>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange">// Adding events</div>
                    <pre>{`span.add_event("user_authenticated", {
    "user.id": user_id,
    "auth.method": "oauth2"
})`}</pre>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* OpenTelemetry SDK Tab */}
        <TabsContent value="opentelemetry" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-grafana-orange" />
                <CardTitle>OpenTelemetry SDK</CardTitle>
              </div>
              <CardDescription>
                Configure and use the OpenTelemetry SDK in your applications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-2">What is OpenTelemetry?</h3>
                <p className="text-gray-600 mb-4">
                  OpenTelemetry (OTel) is a vendor-neutral, open-source observability framework.
                  It provides APIs, SDKs, and tools to instrument, generate, collect, and export telemetry data.
                </p>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Python SDK Setup</h3>
                <div className="space-y-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange"># Install packages</div>
                    <pre>{`pip install opentelemetry-api \\
    opentelemetry-sdk \\
    opentelemetry-exporter-otlp-proto-grpc \\
    opentelemetry-instrumentation-fastapi`}</pre>
                  </div>

                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                    <div className="text-grafana-orange"># Configure exporter</div>
                    <pre>{`from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Set up tracer provider
trace.set_tracer_provider(TracerProvider())

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-gateway:4317",
    insecure=True
)

# Add span processor
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)`}</pre>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Environment Variables</h3>
                <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                  <pre>{`# OTLP Exporter Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-gateway:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Service Configuration
OTEL_SERVICE_NAME=my-service
OTEL_SERVICE_VERSION=1.0.0

# Resource Attributes
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production,service.namespace=api

# Sampling (1.0 = 100%)
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=1.0`}</pre>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Exporters</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-grafana-orange mb-2">OTLP (Recommended)</h4>
                    <p className="text-sm text-gray-600">
                      OpenTelemetry Protocol - works with Tempo, Jaeger, and most backends
                    </p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-grafana-blue mb-2">Jaeger</h4>
                    <p className="text-sm text-gray-600">
                      Native Jaeger exporter for direct export to Jaeger
                    </p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-grafana-green mb-2">Zipkin</h4>
                    <p className="text-sm text-gray-600">
                      Export to Zipkin-compatible backends
                    </p>
                  </div>
                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-grafana-yellow mb-2">Console</h4>
                    <p className="text-sm text-gray-600">
                      Debug exporter that prints to stdout
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">SDK Components</h3>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-grafana-orange rounded-full mt-2"></div>
                    <div>
                      <h4 className="font-semibold">TracerProvider</h4>
                      <p className="text-sm text-gray-600">Factory for creating tracers</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-grafana-blue rounded-full mt-2"></div>
                    <div>
                      <h4 className="font-semibold">Tracer</h4>
                      <p className="text-sm text-gray-600">Creates and manages spans</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-grafana-green rounded-full mt-2"></div>
                    <div>
                      <h4 className="font-semibold">SpanProcessor</h4>
                      <p className="text-sm text-gray-600">Processes spans before export (batching, sampling)</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-grafana-yellow rounded-full mt-2"></div>
                    <div>
                      <h4 className="font-semibold">Exporter</h4>
                      <p className="text-sm text-gray-600">Sends telemetry data to backends</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-grafana-purple rounded-full mt-2"></div>
                    <div>
                      <h4 className="font-semibold">Resource</h4>
                      <p className="text-sm text-gray-600">Service identity and metadata</p>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Pro Tips</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-600">
                  <li>Use environment variables for configuration to avoid hardcoding endpoints</li>
                  <li>Always use BatchSpanProcessor in production for better performance</li>
                  <li>Set meaningful resource attributes (service.name, deployment.environment)</li>
                  <li>Configure sampling to reduce costs in high-volume environments</li>
                  <li>Test with Console exporter during development</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
