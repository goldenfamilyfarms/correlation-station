import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { DocsSidebar } from '@/components/DocsSidebar'
import { TableOfContents } from '@/components/TableOfContents'
import CodeBlock from '@/components/CodeBlock'

export default function DocumentationPage() {
  const [currentSection, setCurrentSection] = useState('overview')
  const [currentSubsection, setCurrentSubsection] = useState('what-is')

  // Handle hash changes for navigation
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1)
      if (hash) {
        setCurrentSubsection(hash)
        // Find which section this subsection belongs to
        const sections = [
          {
            id: 'overview',
            subsections: [{ id: 'what-is' }, { id: 'problems' }, { id: 'architecture-diagram' }],
          },
          {
            id: 'architecture',
            subsections: [
              { id: 'why-grafana' },
              { id: 'why-alloy' },
              { id: 'constraints' },
              { id: 'correlation-engine' },
              { id: 'redis-caching' },
              { id: 'horizontal-scaling' },
            ],
          },
          {
            id: 'query-reference',
            subsections: [{ id: 'logql' }, { id: 'traceql' }, { id: 'promql' }],
          },
        ]
        const section = sections.find((s) => s.subsections.some((sub: { id: string }) => sub.id === hash))
        if (section) {
          setCurrentSection(section.id)
        }
      }
    }

    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  return (
    <div className="flex flex-1 h-full bg-white">
      <DocsSidebar currentSection={currentSection} currentSubsection={currentSubsection} />
      <main className="flex-1 overflow-y-auto bg-white">
        <div className="max-w-4xl mx-auto p-8 space-y-8 prose prose-slate max-w-none">
          {/* Overview Section */}
          <section id="overview" className="space-y-6">
            <div>
              <h1 id="overview-title" className="text-4xl font-bold mb-2">Observability & Correlation Engine Handbook</h1>
              <p className="text-lg text-muted-foreground">
                Comprehensive guide to our observability stack and practices
              </p>
            </div>

            <div id="what-is">
              <h2 id="what-is-correlation-station" className="text-2xl font-semibold mb-4">What is Correlation Station</h2>
              <Card>
                <CardContent className="pt-6">
                  <p className="mb-4">
                    Correlation Station is our internal developer portal and observability hub that provides:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Centralized access to Grafana dashboards (Loki, Tempo, Prometheus, Pyroscope)</li>
                    <li>Automated SECA (Service Engineering & Compliance Automation) error analysis</li>
                    <li>Learning modules for onboarding engineers to observability tools</li>
                    <li>Documentation and runbooks for troubleshooting production issues</li>
                    <li>Real-time monitoring of the Correlation Engine service</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div id="problems">
              <h2 id="problems-solving" className="text-2xl font-semibold mb-4">Problems we were solving</h2>
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <div>
                    <h3 className="font-semibold mb-2">Fragmented Observability</h3>
                    <p className="text-muted-foreground">
                      Multiple tools (DataDog, internal logs, Grafana) with no unified view. Engineers spent
                      too much time context-switching between tools.
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Manual SECA Analysis</h3>
                    <p className="text-muted-foreground">
                      Weekly SECA reviews required manual Excel parsing, Selenium scraping, and traceback
                      extraction. This took hours per week.
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Limited Telemetry</h3>
                    <p className="text-muted-foreground">
                      Sense apps and MDSO lacked comprehensive OpenTelemetry instrumentation, making
                      debugging distributed workflows difficult.
                    </p>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Storage Constraints</h3>
                    <p className="text-muted-foreground">
                      META server storage limits required intelligent log reduction and enrichment before
                      sending to Loki/Tempo.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div id="architecture-diagram">
              <h2 id="architecture-diagram-title" className="text-2xl font-semibold mb-4">High-level architecture diagram</h2>
              <Card>
                <CardContent className="pt-6">
                  <div className="bg-muted rounded-lg p-8 text-center">
                    <p className="text-muted-foreground mb-4">Architecture Diagram</p>
                    <div className="space-y-4 text-sm">
                      <div className="flex justify-center gap-8">
                        <div className="bg-card p-4 rounded border">Sense Apps<br/>(ARDA, BEORN, PALANTIR)</div>
                        <div className="bg-card p-4 rounded border">MDSO</div>
                      </div>
                      <div className="text-[#1B6AC7]">↓ OTEL Spans/Logs/Metrics</div>
                      <div className="bg-card p-4 rounded border mx-auto w-fit">Grafana Alloy Agent</div>
                      <div className="text-[#1B6AC7]">↓</div>
                      <div className="bg-card p-4 rounded border mx-auto w-fit">OTEL Collector (META)</div>
                      <div className="text-[#1B6AC7]">↓</div>
                      <div className="bg-card p-4 rounded border mx-auto w-fit">Correlation Engine</div>
                      <div className="text-[#1B6AC7]">↓</div>
                      <div className="flex justify-center gap-4">
                        <div className="bg-card p-4 rounded border">Loki</div>
                        <div className="bg-card p-4 rounded border">Tempo</div>
                        <div className="bg-card p-4 rounded border">Prometheus</div>
                        <div className="bg-card p-4 rounded border">Pyroscope</div>
                      </div>
                      <div className="text-[#1B6AC7]">↓</div>
                      <div className="bg-card p-4 rounded border mx-auto w-fit">Grafana Dashboards</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>

          <Separator />

          {/* Architecture & Design Decisions */}
          <section id="architecture" className="space-y-6">
            <h1 id="architecture-design" className="text-3xl font-bold">Architecture & Design Decisions</h1>

            <div id="why-grafana">
              <h2 id="why-grafana-title" className="text-2xl font-semibold mb-4">Why Grafana (Loki/Tempo/Prometheus/Pyroscope)</h2>
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li><strong>Open Source:</strong> No vendor lock-in, full control over data</li>
                    <li><strong>Unified Platform:</strong> Single UI for logs, traces, metrics, and profiles</li>
                    <li><strong>Cost Effective:</strong> Self-hosted on META server, no per-GB pricing</li>
                    <li><strong>Query Languages:</strong> LogQL, TraceQL, PromQL provide powerful querying</li>
                    <li><strong>Community:</strong> Active development and large ecosystem</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div id="why-alloy">
              <h2 id="why-alloy-title" className="text-2xl font-semibold mb-4">Why Grafana Alloy agent on MDSO</h2>
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <p>
                    MDSO runs in proprietary Solution Manager containers. We needed a low-invasiveness
                    solution that could collect telemetry without modifying container images.
                  </p>
                  <p>
                    <strong>Alloy agent</strong> runs on the host and tails log files, eliminating the need
                    to hook into each container. This approach:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Requires no container modifications</li>
                    <li>Works with existing log file outputs</li>
                    <li>Can be deployed via systemd service</li>
                    <li>Supports OTLP, Prometheus, and Loki protocols</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div id="constraints">
              <h2 id="constraints-title" className="text-2xl font-semibold mb-4">Constraints of Solution Manager / proprietary containers</h2>
              <Card>
                <CardContent className="pt-6">
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Cannot modify container images</li>
                    <li>Limited ability to inject sidecars</li>
                    <li>Log files are written to host filesystem</li>
                    <li>Network access to META server required</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div id="correlation-engine">
              <h2 id="correlation-engine-title" className="text-2xl font-semibold mb-4">Why a Correlation Engine before data stores</h2>
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <p>
                    <strong>META storage limits</strong> require intelligent log reduction. The Correlation Engine:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Shrinks logs by removing redundant information</li>
                    <li>Normalizes fields across different services</li>
                    <li>Enriches with correlation IDs and metadata</li>
                    <li>Compacts related events into single log entries</li>
                    <li>Filters noise before sending to Loki/Tempo</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div id="redis-caching">
              <h2 id="redis-caching-title" className="text-2xl font-semibold mb-4">Redis caching & backpressure handling</h2>
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <p>
                    The Correlation Engine uses Redis to cache <strong>partial traces</strong> until they
                    are complete. This enables:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Correlating spans from multiple services</li>
                    <li>Handling backpressure when data stores are slow</li>
                    <li>Preventing queue buildup in the engine</li>
                    <li>TTL-based expiration of stale traces (48 hours)</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div id="horizontal-scaling">
              <h2 id="horizontal-scaling-title" className="text-2xl font-semibold mb-4">Horizontal scaling with multiple correlation engine instances + gateway</h2>
              <Card>
                <CardContent className="pt-6">
                  <p>
                    Multiple Correlation Engine instances can run behind a gateway. The gateway:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>Load balances OTLP traffic</li>
                    <li>Routes to available engine instances</li>
                    <li>Handles health checks and failover</li>
                    <li>Shares Redis cache across instances</li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </section>

          <Separator />

          {/* Query Reference - Keep existing content but reorganize */}
          <section id="query-reference" className="space-y-6">
            <h1 id="query-reference-title" className="text-3xl font-bold">Query Reference</h1>

            <div id="traceql">
              <h2 id="traceql-examples" className="text-2xl font-semibold mb-4">TraceQL Examples</h2>
              <Card>
                <CardHeader>
                  <CardTitle>TraceQL - Trace Query Language</CardTitle>
                  <CardDescription>Query and analyze distributed traces in Grafana Tempo</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h3 className="font-semibold mb-2">Basic Syntax</h3>
                    <CodeBlock language="traceql" code={`// Find all traces for a specific service
{ .service.name = "auth-service" }

// Find traces with errors
{ status = error }

// Find slow traces (duration > 1s)
{ duration > 1s }`} />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Advanced Queries</h3>
                    <CodeBlock language="traceql" code={`// Combine multiple conditions
{ .service.name = "api-gateway" && status = error && duration > 500ms }

// Filter by resource attributes
{ resource.deployment.environment = "production" && .http.status_code >= 500 }

// Search for specific span names
{ name = "database-query" && duration > 100ms }`} />
                  </div>
                </CardContent>
              </Card>
            </div>

            <div id="logql">
              <h2 id="logql-examples" className="text-2xl font-semibold mb-4">LogQL Examples</h2>
              <Card>
                <CardHeader>
                  <CardTitle>LogQL - Log Query Language</CardTitle>
                  <CardDescription>Query logs in Grafana Loki</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <CodeBlock language="logql" code={`// Simple log stream selector
{service="arda"} |= "error"

// Filter by log level
{service="beorn"} | json | level="ERROR"

// Extract fields and aggregate
{service="palantir"} | json | sum(count_over_time({service="palantir"}[5m])) by (circuit_id)

// Rate queries
rate({service="correlation-engine"}[5m])`} />
                </CardContent>
              </Card>
            </div>

            <div id="promql">
              <h2 id="promql-examples" className="text-2xl font-semibold mb-4">PromQL Examples</h2>
              <Card>
                <CardHeader>
                  <CardTitle>PromQL - Prometheus Query Language</CardTitle>
                  <CardDescription>Query metrics in Prometheus</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <CodeBlock language="promql" code={`// Simple metric query
http_requests_total{service="arda"}

// Rate calculation
rate(http_requests_total[5m])

// Aggregation
sum(rate(http_requests_total[5m])) by (service)

// Percentiles
histogram_quantile(0.95, http_request_duration_seconds_bucket)`} />
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Add more sections as needed - keeping it concise for now */}
          <section id="faq" className="space-y-6">
            <h1 id="faq-glossary" className="text-3xl font-bold">FAQ & Glossary</h1>
            <Card>
              <CardContent className="pt-6 space-y-4">
                <div>
                  <h3 id="what-is-span" className="font-semibold mb-2">What is a span?</h3>
                  <p className="text-muted-foreground">
                    A span represents a single operation within a trace. It has a start time, duration,
                    and attributes.
                  </p>
                </div>
                <div>
                  <h3 id="what-is-trace" className="font-semibold mb-2">What is a trace?</h3>
                  <p className="text-muted-foreground">
                    A trace is a collection of spans that represent a request as it flows through
                    multiple services.
                  </p>
                </div>
              </CardContent>
            </Card>
          </section>
        </div>
      </main>
      <TableOfContents contentSelector="main" />
    </div>
  )
}

