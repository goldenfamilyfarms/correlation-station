import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { ChevronLeft, ChevronRight, BookOpen, Code2, Lightbulb } from 'lucide-react'
import CodeBlock from '@/components/CodeBlock'

export default function DocumentationPage() {
  const [activeTab, setActiveTab] = useState('overview')

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BookOpen },
    { id: 'architecture', label: 'Architecture', icon: Lightbulb },
    { id: 'query-reference', label: 'Query Reference', icon: Code2 },
  ]

  const getNextTab = () => {
    const currentIndex = tabs.findIndex((t) => t.id === activeTab)
    return currentIndex < tabs.length - 1 ? tabs[currentIndex + 1] : null
  }

  const getPrevTab = () => {
    const currentIndex = tabs.findIndex((t) => t.id === activeTab)
    return currentIndex > 0 ? tabs[currentIndex - 1] : null
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="space-y-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-3">
            Observability & Correlation Engine
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-3xl">
            Comprehensive guide to our observability stack, correlation engine, and best practices for monitoring distributed systems
          </p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline" className="text-xs">v2.1.0</Badge>
          <Badge variant="outline" className="text-xs">Updated Dec 2025</Badge>
        </div>
      </div>

      <Separator className="my-8" />

      {/* Horizontal Tab Navigation */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-8 h-12">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className="flex items-center gap-2 text-sm md:text-base"
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.label.split(' ')[0]}</span>
              </TabsTrigger>
            )
          })}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-8">
          <section className="space-y-6">
            <div>
              <h2 className="text-3xl font-bold mb-4">What is Correlation Station?</h2>
              <Card className="hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <p className="text-base leading-relaxed mb-4">
                    Correlation Station is our internal developer portal and observability hub that provides:
                  </p>
                  <ul className="space-y-3 ml-6">
                    <li className="flex items-start gap-3">
                      <span className="text-primary mt-1">•</span>
                      <span className="leading-relaxed">Centralized access to Grafana dashboards (Loki, Tempo, Prometheus, Pyroscope)</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="text-primary mt-1">•</span>
                      <span className="leading-relaxed">Automated SECA (Service Engineering & Compliance Automation) error analysis</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="text-primary mt-1">•</span>
                      <span className="leading-relaxed">Learning modules for onboarding engineers to observability tools</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="text-primary mt-1">•</span>
                      <span className="leading-relaxed">Documentation and runbooks for troubleshooting production issues</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="text-primary mt-1">•</span>
                      <span className="leading-relaxed">Real-time monitoring of the Correlation Engine service</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div>
              <h2 className="text-3xl font-bold mb-4">Problems We Were Solving</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-lg">Fragmented Observability</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">
                      Multiple tools (DataDog, internal logs, Grafana) with no unified view. Engineers spent
                      too much time context-switching between tools.
                    </p>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-lg">Manual SECA Analysis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">
                      Weekly SECA reviews required manual Excel parsing, Selenium scraping, and traceback
                      extraction. This took hours per week.
                    </p>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-lg">Limited Telemetry</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">
                      Sense apps and MDSO lacked comprehensive OpenTelemetry instrumentation, making
                      debugging distributed workflows difficult.
                    </p>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-lg">Storage Constraints</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">
                      META server storage limits required intelligent log reduction and enrichment before
                      sending to Loki/Tempo.
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div>
              <h2 className="text-3xl font-bold mb-4">High-Level Architecture</h2>
              <Card className="bg-muted/30">
                <CardContent className="pt-6">
                  <div className="space-y-6 text-center">
                    <div className="flex justify-center gap-6 flex-wrap">
                      <div className="bg-card p-4 rounded-lg border-2 shadow-sm min-w-[140px]">
                        <div className="font-semibold">Sense Apps</div>
                        <div className="text-xs text-muted-foreground mt-1">ARDA, BEORN, PALANTIR</div>
                      </div>
                      <div className="bg-card p-4 rounded-lg border-2 shadow-sm min-w-[140px]">
                        <div className="font-semibold">MDSO</div>
                        <div className="text-xs text-muted-foreground mt-1">Service Orchestration</div>
                      </div>
                    </div>

                    <div className="text-primary font-medium flex items-center justify-center gap-2">
                      <ChevronRight className="rotate-90 h-5 w-5" />
                      <span>OTEL Spans/Logs/Metrics</span>
                      <ChevronRight className="rotate-90 h-5 w-5" />
                    </div>

                    <div className="bg-card p-4 rounded-lg border-2 shadow-sm mx-auto max-w-xs">
                      <div className="font-semibold">Grafana Alloy Agent</div>
                    </div>

                    <div className="text-primary font-medium flex items-center justify-center gap-2">
                      <ChevronRight className="rotate-90 h-5 w-5" />
                    </div>

                    <div className="bg-card p-4 rounded-lg border-2 shadow-sm mx-auto max-w-xs">
                      <div className="font-semibold">OTEL Collector</div>
                      <div className="text-xs text-muted-foreground mt-1">META Server</div>
                    </div>

                    <div className="text-primary font-medium flex items-center justify-center gap-2">
                      <ChevronRight className="rotate-90 h-5 w-5" />
                    </div>

                    <div className="bg-primary/10 p-4 rounded-lg border-2 border-primary shadow-sm mx-auto max-w-xs">
                      <div className="font-semibold">Correlation Engine</div>
                      <div className="text-xs text-muted-foreground mt-1">Redis + Processing</div>
                    </div>

                    <div className="text-primary font-medium flex items-center justify-center gap-2">
                      <ChevronRight className="rotate-90 h-5 w-5" />
                    </div>

                    <div className="flex justify-center gap-4 flex-wrap">
                      <div className="bg-card p-3 rounded-lg border shadow-sm">Loki</div>
                      <div className="bg-card p-3 rounded-lg border shadow-sm">Tempo</div>
                      <div className="bg-card p-3 rounded-lg border shadow-sm">Prometheus</div>
                      <div className="bg-card p-3 rounded-lg border shadow-sm">Pyroscope</div>
                    </div>

                    <div className="text-primary font-medium flex items-center justify-center gap-2">
                      <ChevronRight className="rotate-90 h-5 w-5" />
                    </div>

                    <div className="bg-accent/20 p-4 rounded-lg border-2 border-accent shadow-sm mx-auto max-w-xs">
                      <div className="font-semibold">Grafana Dashboards</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>
        </TabsContent>

        {/* Architecture Tab */}
        <TabsContent value="architecture" className="space-y-8">
          <section className="space-y-6">
            <h2 className="text-3xl font-bold">Architecture & Design Decisions</h2>

            <div className="space-y-6">
              <Card className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="text-2xl">Why Grafana Stack?</span>
                  </CardTitle>
                  <CardDescription>Loki, Tempo, Prometheus, Pyroscope</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    <li className="flex items-start gap-3">
                      <Badge variant="outline" className="mt-1">Open Source</Badge>
                      <span className="leading-relaxed">No vendor lock-in, full control over data</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <Badge variant="outline" className="mt-1">Unified</Badge>
                      <span className="leading-relaxed">Single UI for logs, traces, metrics, and profiles</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <Badge variant="outline" className="mt-1">Cost Effective</Badge>
                      <span className="leading-relaxed">Self-hosted on META server, no per-GB pricing</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <Badge variant="outline" className="mt-1">Powerful</Badge>
                      <span className="leading-relaxed">LogQL, TraceQL, PromQL provide advanced querying</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <Badge variant="outline" className="mt-1">Community</Badge>
                      <span className="leading-relaxed">Active development and large ecosystem</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-2xl">Grafana Alloy Agent on MDSO</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="leading-relaxed">
                    MDSO runs in proprietary Solution Manager containers. We needed a low-invasiveness
                    solution that could collect telemetry without modifying container images.
                  </p>
                  <p className="leading-relaxed">
                    <strong>Alloy agent</strong> runs on the host and tails log files, eliminating the need
                    to hook into each container:
                  </p>
                  <ul className="space-y-2 ml-6">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Requires no container modifications</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Works with existing log file outputs</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Can be deployed via systemd service</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Supports OTLP, Prometheus, and Loki protocols</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-2xl">Correlation Engine Design</CardTitle>
                  <CardDescription>Why process data before storage?</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="leading-relaxed">
                    <strong>META storage limits</strong> require intelligent log reduction. The Correlation Engine:
                  </p>
                  <ul className="space-y-2 ml-6">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Shrinks logs by removing redundant information</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Normalizes fields across different services</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Enriches with correlation IDs and metadata</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Compacts related events into single log entries</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Filters noise before sending to Loki/Tempo</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-2xl">Redis Caching & Backpressure</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="leading-relaxed">
                    The Correlation Engine uses Redis to cache <strong>partial traces</strong> until they
                    are complete. This enables:
                  </p>
                  <ul className="space-y-2 ml-6">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Correlating spans from multiple services</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Handling backpressure when data stores are slow</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Preventing queue buildup in the engine</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>TTL-based expiration of stale traces (48 hours)</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-2xl">Horizontal Scaling</CardTitle>
                  <CardDescription>Multiple instances + gateway</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="leading-relaxed mb-4">
                    Multiple Correlation Engine instances can run behind a gateway. The gateway:
                  </p>
                  <ul className="space-y-2 ml-6">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Load balances OTLP traffic</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Routes to available engine instances</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Handles health checks and failover</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      <span>Shares Redis cache across instances</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </section>
        </TabsContent>

        {/* Query Reference Tab */}
        <TabsContent value="query-reference" className="space-y-8">
          <section className="space-y-6">
            <h2 className="text-3xl font-bold">Query Reference</h2>

            <Card>
              <CardHeader>
                <CardTitle className="text-2xl">TraceQL - Trace Query Language</CardTitle>
                <CardDescription>Query and analyze distributed traces in Grafana Tempo</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="font-semibold text-lg mb-3">Basic Syntax</h3>
                  <CodeBlock language="traceql" code={`// Find all traces for a specific service
{ .service.name = "auth-service" }

// Find traces with errors
{ status = error }

// Find slow traces (duration > 1s)
{ duration > 1s }`} />
                </div>
                <div>
                  <h3 className="font-semibold text-lg mb-3">Advanced Queries</h3>
                  <CodeBlock language="traceql" code={`// Combine multiple conditions
{ .service.name = "api-gateway" && status = error && duration > 500ms }

// Filter by resource attributes
{ resource.deployment.environment = "production" && .http.status_code >= 500 }

// Search for specific span names
{ name = "database-query" && duration > 100ms }`} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-2xl">LogQL - Log Query Language</CardTitle>
                <CardDescription>Query logs in Grafana Loki</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
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

            <Card>
              <CardHeader>
                <CardTitle className="text-2xl">PromQL - Prometheus Query Language</CardTitle>
                <CardDescription>Query metrics in Prometheus</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
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
          </section>
        </TabsContent>
      </Tabs>

      {/* Prev/Next Navigation */}
      <Separator className="my-8" />
      <div className="flex justify-between items-center pt-4">
        {getPrevTab() ? (
          <Button
            variant="outline"
            onClick={() => setActiveTab(getPrevTab()!.id)}
            className="flex items-center gap-2"
          >
            <ChevronLeft className="h-4 w-4" />
            <div className="text-left">
              <div className="text-xs text-muted-foreground">Previous</div>
              <div className="font-medium">{getPrevTab()!.label}</div>
            </div>
          </Button>
        ) : (
          <div />
        )}

        {getNextTab() ? (
          <Button
            variant="outline"
            onClick={() => setActiveTab(getNextTab()!.id)}
            className="flex items-center gap-2"
          >
            <div className="text-right">
              <div className="text-xs text-muted-foreground">Next</div>
              <div className="font-medium">{getNextTab()!.label}</div>
            </div>
            <ChevronRight className="h-4 w-4" />
          </Button>
        ) : (
          <div />
        )}
      </div>
    </div>
  )
}
