import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Server, Database, Activity, Layers, GitBranch, Zap } from 'lucide-react'

export default function ArchitecturePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">System Architecture</h1>
        <p className="text-lg text-gray-600">
          Comprehensive overview of our distributed observability platform
        </p>
      </div>

      {/* High-Level Architecture */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-grafana-orange" />
            <CardTitle>High-Level Architecture</CardTitle>
          </div>
          <CardDescription>
            Our observability stack follows the LGTM pattern (Loki, Grafana, Tempo, Mimir/Prometheus)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="bg-gray-50 p-6 rounded-lg border-2 border-gray-200">
            <pre className="text-sm overflow-x-auto">
{`┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Service A  │  │   Service B  │  │   Service C  │              │
│  │  (FastAPI)   │  │   (FastAPI)  │  │   (FastAPI)  │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │ OTLP             │ OTLP             │ OTLP                 │
└─────────┼──────────────────┼──────────────────┼──────────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  OTel Gateway   │ ← Receives all telemetry
                    │   (Collector)   │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐
  │  Grafana Loki │  │ Grafana Tempo│  │ Prometheus  │
  │    (Logs)     │  │   (Traces)   │  │  (Metrics)  │
  └───────┬───────┘  └──────┬───────┘  └──────┬──────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │     Grafana     │ ← Visualization & Queries
                    │       UI        │
                    └─────────────────┘`}
            </pre>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-orange-50 p-4 rounded-lg">
              <h4 className="font-semibold text-grafana-orange mb-2 flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Correlation Engine
              </h4>
              <p className="text-sm text-gray-600">
                Custom service that correlates logs and traces by trace_id within 60-second windows.
                Enriches data and exports to multiple backends.
              </p>
            </div>
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-grafana-blue mb-2 flex items-center gap-2">
                <Server className="h-4 w-4" />
                OTel Gateway
              </h4>
              <p className="text-sm text-gray-600">
                Central collector for all OpenTelemetry data. Handles protocol conversion,
                batching, and routing to appropriate backends.
              </p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h4 className="font-semibold text-grafana-green mb-2 flex items-center gap-2">
                <Database className="h-4 w-4" />
                Storage Backends
              </h4>
              <p className="text-sm text-gray-600">
                Loki for logs, Tempo for traces, Prometheus for metrics. Each optimized for
                their respective data types with low-cardinality designs.
              </p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <h4 className="font-semibold text-grafana-yellow mb-2 flex items-center gap-2">
                <Zap className="h-4 w-4" />
                Grafana UI
              </h4>
              <p className="text-sm text-gray-600">
                Unified interface for querying and visualizing all telemetry data.
                Supports TraceQL, LogQL, and PromQL queries.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Service Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-grafana-orange" />
            <CardTitle>Service Components</CardTitle>
          </div>
          <CardDescription>
            Detailed breakdown of each service in our observability stack
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Grafana */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-grafana-orange/10 rounded-lg flex items-center justify-center">
                <Activity className="h-5 w-5 text-grafana-orange" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Grafana 10.2.0</h3>
                <p className="text-sm text-gray-500">Visualization & Dashboards</p>
              </div>
            </div>
            <div className="ml-13 space-y-2 text-sm text-gray-600">
              <p><strong>Port:</strong> 8443</p>
              <p><strong>Purpose:</strong> Unified UI for querying logs, traces, and metrics</p>
              <p><strong>Features:</strong></p>
              <ul className="list-disc list-inside ml-4">
                <li>Pre-configured dashboards for correlation analysis</li>
                <li>Trace-to-logs navigation with automatic correlation</li>
                <li>TraceQL, LogQL, and PromQL query editors</li>
                <li>Alert management and notification channels</li>
              </ul>
            </div>
          </div>

          <Separator />

          {/* Loki */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-grafana-green/10 rounded-lg flex items-center justify-center">
                <Database className="h-5 w-5 text-grafana-green" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Loki 2.9.2</h3>
                <p className="text-sm text-gray-500">Log Aggregation System</p>
              </div>
            </div>
            <div className="ml-13 space-y-2 text-sm text-gray-600">
              <p><strong>Port:</strong> 3100</p>
              <p><strong>Purpose:</strong> Horizontally scalable log aggregation inspired by Prometheus</p>
              <p><strong>Design:</strong></p>
              <ul className="list-disc list-inside ml-4">
                <li>Only 3 labels: service, level, trace_id (low-cardinality)</li>
                <li>Stores log content as compressed chunks</li>
                <li>Index-free for cost efficiency</li>
                <li>15-day retention policy</li>
              </ul>
            </div>
          </div>

          <Separator />

          {/* Tempo */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-grafana-blue/10 rounded-lg flex items-center justify-center">
                <GitBranch className="h-5 w-5 text-grafana-blue" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Tempo 2.3.0</h3>
                <p className="text-sm text-gray-500">Distributed Tracing Backend</p>
              </div>
            </div>
            <div className="ml-13 space-y-2 text-sm text-gray-600">
              <p><strong>Port:</strong> 3200 (HTTP), 4317 (OTLP gRPC), 4318 (OTLP HTTP)</p>
              <p><strong>Purpose:</strong> Cost-effective distributed tracing storage</p>
              <p><strong>Features:</strong></p>
              <ul className="list-disc list-inside ml-4">
                <li>Native OTLP ingestion (gRPC and HTTP)</li>
                <li>TraceQL support for advanced queries</li>
                <li>Service graph generation</li>
                <li>Integration with Loki for trace-to-logs correlation</li>
              </ul>
            </div>
          </div>

          <Separator />

          {/* Prometheus */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-grafana-red/10 rounded-lg flex items-center justify-center">
                <Zap className="h-5 w-5 text-grafana-red" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Prometheus 2.48.0</h3>
                <p className="text-sm text-gray-500">Metrics & Monitoring</p>
              </div>
            </div>
            <div className="ml-13 space-y-2 text-sm text-gray-600">
              <p><strong>Port:</strong> 9090</p>
              <p><strong>Purpose:</strong> Time-series metrics storage and querying</p>
              <p><strong>Configuration:</strong></p>
              <ul className="list-disc list-inside ml-4">
                <li>15-day retention period</li>
                <li>Scrapes correlation engine /metrics endpoint</li>
                <li>Tracks request rates, latencies, error rates</li>
                <li>PromQL for queries and alerting</li>
              </ul>
            </div>
          </div>

          <Separator />

          {/* Pyroscope */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-grafana-purple/10 rounded-lg flex items-center justify-center">
                <Activity className="h-5 w-5 text-grafana-purple" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Pyroscope (Latest)</h3>
                <p className="text-sm text-gray-500">Continuous Profiling</p>
              </div>
            </div>
            <div className="ml-13 space-y-2 text-sm text-gray-600">
              <p><strong>Port:</strong> 4040</p>
              <p><strong>Purpose:</strong> Performance profiling and optimization</p>
              <p><strong>Capabilities:</strong></p>
              <ul className="list-disc list-inside ml-4">
                <li>CPU profiling for identifying bottlenecks</li>
                <li>Memory profiling for leak detection</li>
                <li>Flame graphs for visualization</li>
                <li>Tag-based filtering by service and environment</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Flow */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-grafana-orange" />
            <CardTitle>Telemetry Data Flow</CardTitle>
          </div>
          <CardDescription>
            How observability data flows through the system
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-grafana-orange rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white">
                1
              </div>
              <div>
                <h4 className="font-semibold mb-1">Instrumentation</h4>
                <p className="text-sm text-gray-600">
                  Applications use OpenTelemetry SDKs to generate logs, traces, and metrics.
                  Auto-instrumentation libraries capture HTTP requests, database queries, and more.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-grafana-blue rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white">
                2
              </div>
              <div>
                <h4 className="font-semibold mb-1">Export via OTLP</h4>
                <p className="text-sm text-gray-600">
                  Telemetry data is exported using the OpenTelemetry Protocol (OTLP) over gRPC or HTTP.
                  All services send data to a single endpoint: the OTel Gateway.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-grafana-green rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white">
                3
              </div>
              <div>
                <h4 className="font-semibold mb-1">Gateway Processing</h4>
                <p className="text-sm text-gray-600">
                  The OTel Collector receives OTLP data, batches it, and routes to appropriate backends.
                  It can also filter, transform, and sample data before export.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-grafana-yellow rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white">
                4
              </div>
              <div>
                <h4 className="font-semibold mb-1">Correlation Engine</h4>
                <p className="text-sm text-gray-600">
                  A custom service correlates logs and traces by trace_id within 60-second windows.
                  It enriches data with correlation metadata and exports to Loki/Tempo.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-grafana-red rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white">
                5
              </div>
              <div>
                <h4 className="font-semibold mb-1">Storage</h4>
                <p className="text-sm text-gray-600">
                  Data is stored in specialized backends: Loki (logs), Tempo (traces), Prometheus (metrics).
                  Each backend is optimized for its data type with retention policies.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-grafana-purple rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white">
                6
              </div>
              <div>
                <h4 className="font-semibold mb-1">Visualization</h4>
                <p className="text-sm text-gray-600">
                  Grafana queries all backends using their respective query languages (LogQL, TraceQL, PromQL).
                  Pre-built dashboards provide instant visibility into system behavior.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Design Principles */}
      <Card>
        <CardHeader>
          <CardTitle>Design Principles</CardTitle>
          <CardDescription>
            Key architectural decisions and their rationale
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border-l-4 border-grafana-orange pl-4">
              <h4 className="font-semibold mb-1">Low Cardinality</h4>
              <p className="text-sm text-gray-600">
                Limited label sets (only 3 in Loki) prevent metric explosion and keep costs low
                while maintaining queryability.
              </p>
            </div>

            <div className="border-l-4 border-grafana-blue pl-4">
              <h4 className="font-semibold mb-1">Vendor Neutrality</h4>
              <p className="text-sm text-gray-600">
                OpenTelemetry standard ensures no vendor lock-in. Can switch backends without
                changing instrumentation.
              </p>
            </div>

            <div className="border-l-4 border-grafana-green pl-4">
              <h4 className="font-semibold mb-1">Correlation-First</h4>
              <p className="text-sm text-gray-600">
                trace_id links logs and traces automatically. Navigate from trace spans to related
                logs seamlessly.
              </p>
            </div>

            <div className="border-l-4 border-grafana-yellow pl-4">
              <h4 className="font-semibold mb-1">Horizontal Scalability</h4>
              <p className="text-sm text-gray-600">
                All components can scale horizontally. Add more collectors, storage nodes, or
                query frontends as needed.
              </p>
            </div>

            <div className="border-l-4 border-grafana-red pl-4">
              <h4 className="font-semibold mb-1">Cost Efficiency</h4>
              <p className="text-sm text-gray-600">
                Open-source stack, efficient storage formats, and smart retention policies keep
                costs predictable and low.
              </p>
            </div>

            <div className="border-l-4 border-grafana-purple pl-4">
              <h4 className="font-semibold mb-1">Developer Experience</h4>
              <p className="text-sm text-gray-600">
                Auto-instrumentation libraries, comprehensive docs, and intuitive UIs make
                observability accessible to all engineers.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Network Diagram */}
      <Card>
        <CardHeader>
          <CardTitle>Network Configuration</CardTitle>
          <CardDescription>
            Docker network topology and port mappings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-50 p-4 rounded-lg border-2 border-gray-200">
            <div className="space-y-2 text-sm font-mono">
              <p><strong>Network:</strong> observability (bridge) - 172.20.0.0/23</p>
              <Separator className="my-2" />
              <p><strong>Exposed Ports:</strong></p>
              <ul className="ml-4 space-y-1">
                <li>• 8443 → Grafana UI</li>
                <li>• 3100 → Loki API</li>
                <li>• 9000 → Tempo HTTP API</li>
                <li>• 9090 → Prometheus UI</li>
                <li>• 4040 → Pyroscope UI</li>
                <li>• 8080 → Correlation Engine API</li>
                <li>• 55681 → OTel Gateway OTLP HTTP</li>
                <li>• 8888 → OTel Gateway Metrics</li>
                <li>• 3000 → Correlation Station UI</li>
              </ul>
              <Separator className="my-2" />
              <p><strong>Internal Only:</strong></p>
              <ul className="ml-4 space-y-1">
                <li>• 4317 → OTel Gateway OTLP gRPC (internal)</li>
                <li>• 4318 → Tempo OTLP HTTP (internal)</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
