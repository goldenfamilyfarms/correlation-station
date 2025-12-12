import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Database, 
  Activity, 
  Network, 
  Zap, 
  ExternalLink
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface Service {
  name: string
  category: 'Orchestration' | 'Web App' | 'Gateway' | 'Observability' | 'Control Plane'
  description: string
  responsibilities: string[]
  integrations: string[]
  observability: string
  repo?: string
  api?: string
  dashboard?: string
}

const services: Service[] = [
  {
    name: 'MDSO',
    category: 'Orchestration',
    description: 'Multi-Domain Service Orchestrator - Manages product lifecycle and service provisioning',
    responsibilities: ['Product lifecycle management', 'Service orchestration', 'Compliance validation'],
    integrations: ['Sense apps', 'IP Control', 'Kong', 'Granite'],
    observability: 'OTEL spans via Alloy agent, logs tailed from host filesystem',
    dashboard: 'http://159.56.4.94:3000',
  },
  {
    name: 'Sense',
    category: 'Orchestration',
    description: 'Service Engineering Automation - ARDA, BEORN, PALANTIR microservices',
    responsibilities: ['Circuit design (ARDA)', 'Eligibility checks (BEORN)', 'Device provisioning (PALANTIR)'],
    integrations: ['MDSO', 'IP Control', 'Kong', 'Granite', 'TACACS', 'SNMP'],
    observability: 'OTEL SDK instrumentation, traces/logs/metrics exported to Correlation Engine',
    repo: 'https://gitlab.com/service-engineering-automation/sense',
  },
  {
    name: 'IP Control',
    category: 'Control Plane',
    description: 'IP Address Management (IPAM) system',
    responsibilities: ['IP allocation', 'Subnet management', 'DNS record management'],
    integrations: ['Sense apps', 'MDSO'],
    observability: 'API call tracing via Sense apps',
  },
  {
    name: 'Kong',
    category: 'Gateway',
    description: 'API Gateway for authentication and routing',
    responsibilities: ['API authentication', 'Request routing', 'Rate limiting'],
    integrations: ['All services'],
    observability: 'Access logs, metrics exported to Prometheus',
  },
  {
    name: 'Expo',
    category: 'Web App',
    description: 'Order capture and management system',
    responsibilities: ['Order entry', 'Customer portal', 'Order tracking'],
    integrations: ['Kong', 'MDSO'],
    observability: 'Application logs, API metrics',
  },
  {
    name: 'Moonshot',
    category: 'Web App',
    description: 'Strategic application for service management',
    responsibilities: ['Service management', 'Customer portal'],
    integrations: ['Kong', 'MDSO', 'Sense'],
    observability: 'Application logs, API traces',
  },
  {
    name: 'Titan',
    category: 'Web App',
    description: 'Strategic application for network operations',
    responsibilities: ['Network operations', 'Service management'],
    integrations: ['Kong', 'MDSO'],
    observability: 'Application logs, API traces',
  },
  {
    name: 'Temple',
    category: 'Web App',
    description: 'Strategic application for service delivery',
    responsibilities: ['Service delivery', 'Customer management'],
    integrations: ['Kong', 'MDSO'],
    observability: 'Application logs, API traces',
  },
  {
    name: 'Galaxy',
    category: 'Web App',
    description: 'Strategic application for service catalog',
    responsibilities: ['Service catalog', 'Product management'],
    integrations: ['Kong', 'MDSO'],
    observability: 'Application logs, API traces',
  },
  {
    name: 'Correlation Engine',
    category: 'Observability',
    description: 'Custom service that correlates, enriches, and compacts telemetry before data stores',
    responsibilities: ['Log correlation', 'Trace enrichment', 'Data compaction', 'Backpressure handling'],
    integrations: ['OTEL Collector', 'Redis', 'Loki', 'Tempo', 'Prometheus'],
    observability: 'Self-monitoring via Prometheus metrics, logs in Loki',
    dashboard: 'http://159.56.4.94:3000',
  },
  {
    name: 'Grafana Stack',
    category: 'Observability',
    description: 'LGTM stack: Loki, Grafana, Tempo, Mimir/Prometheus, Pyroscope',
    responsibilities: ['Log storage (Loki)', 'Trace storage (Tempo)', 'Metrics (Prometheus)', 'Profiling (Pyroscope)'],
    integrations: ['Correlation Engine', 'OTEL Collector'],
    observability: 'Self-monitoring dashboards',
    dashboard: 'http://159.56.4.94:3000',
  },
]

const systemMapNodes = [
  { id: 'mdso', name: 'MDSO', x: 50, y: 20, category: 'Orchestration' },
  { id: 'sense', name: 'Sense', x: 50, y: 40, category: 'Orchestration' },
  { id: 'ip-control', name: 'IP Control', x: 20, y: 40, category: 'Control Plane' },
  { id: 'kong', name: 'Kong', x: 80, y: 40, category: 'Gateway' },
  { id: 'expo', name: 'Expo', x: 10, y: 60, category: 'Web App' },
  { id: 'moonshot', name: 'Moonshot', x: 30, y: 60, category: 'Web App' },
  { id: 'titan', name: 'Titan', x: 50, y: 60, category: 'Web App' },
  { id: 'temple', name: 'Temple', x: 70, y: 60, category: 'Web App' },
  { id: 'galaxy', name: 'Galaxy', x: 90, y: 60, category: 'Web App' },
  { id: 'correlation-engine', name: 'Correlation Engine', x: 50, y: 80, category: 'Observability' },
  { id: 'grafana-stack', name: 'Grafana Stack', x: 50, y: 100, category: 'Observability' },
]

const lifecycleSteps = [
  { step: 1, name: 'Order Capture', systems: ['Expo', 'Galaxy', 'Moonshot', 'Titan', 'Temple'] },
  { step: 2, name: 'Kong API Gateway', systems: ['Kong'] },
  { step: 3, name: 'Orchestration', systems: ['MDSO', 'Sense'] },
  { step: 4, name: 'Network Provisioning', systems: ['IP Control'] },
  { step: 5, name: 'Compliance & Validation', systems: ['MDSO', 'Sense'] },
  { step: 6, name: 'Monitoring & Feedback', systems: ['Correlation Engine', 'Grafana Stack'] },
]

export default function ArchitecturePage() {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [selectedService, setSelectedService] = useState<Service | null>(null)

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Orchestration':
        return 'bg-primary/20 text-primary border-primary'
      case 'Web App':
        return 'bg-accent/20 text-accent border-accent'
      case 'Gateway':
        return 'bg-[#1B6AC7]/20 text-[#1B6AC7] border-[#1B6AC7]'
      case 'Observability':
        return 'bg-green-500/20 text-green-500 border-green-500'
      case 'Control Plane':
        return 'bg-purple-500/20 text-purple-500 border-purple-500'
      default:
        return 'bg-muted text-muted-foreground border-border'
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">SEEFA Architecture</h1>
        <p className="text-muted-foreground">
          How our automation platforms, web apps, and observability stack fit together
        </p>
      </div>

      {/* System Map */}
      <Card>
        <CardHeader>
          <CardTitle>System Map</CardTitle>
          <CardDescription>Interactive diagram of all systems and their relationships</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative bg-muted rounded-lg p-8 min-h-[400px]">
            <svg className="w-full h-full absolute inset-0" viewBox="0 0 100 100" preserveAspectRatio="none">
              {/* Draw connections */}
              {systemMapNodes.map((node) => {
                if (node.id === 'correlation-engine' || node.id === 'grafana-stack') return null
                return (
                  <line
                    key={`line-${node.id}`}
                    x1={node.x}
                    y1={node.y}
                    x2={50}
                    y2={80}
                    stroke="currentColor"
                    strokeWidth="0.5"
                    className="text-muted-foreground opacity-30"
                  />
                )
              })}
            </svg>
            <div className="relative grid grid-cols-5 gap-4">
              {systemMapNodes.map((node) => {
                const service = services.find((s) => s.name.toLowerCase().replace(/\s+/g, '-') === node.id)
                return (
                  <TooltipProvider key={node.id}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div
                          className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                            hoveredNode === node.id
                              ? 'scale-105 shadow-lg'
                              : 'hover:scale-102'
                          } ${getCategoryColor(node.category)}`}
                          onMouseEnter={() => setHoveredNode(node.id)}
                          onMouseLeave={() => setHoveredNode(null)}
                          onClick={() => {
                            const svc = services.find((s) => s.name.toLowerCase().replace(/\s+/g, '-') === node.id)
                            if (svc) {
                              setSelectedService(svc)
                              document.getElementById('service-catalog')?.scrollIntoView({ behavior: 'smooth' })
                            }
                          }}
                        >
                          <div className="font-semibold text-sm">{node.name}</div>
                          <div className="text-xs mt-1 opacity-70">{node.category}</div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <div className="max-w-xs">
                          <p className="font-semibold">{node.name}</p>
                          {service && <p className="text-xs mt-1">{service.description}</p>}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="mt-2 h-6 text-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              const svc = services.find((s) => s.name.toLowerCase().replace(/\s+/g, '-') === node.id)
                              if (svc) setSelectedService(svc)
                            }}
                          >
                            View details
                          </Button>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Service Catalog */}
      <div id="service-catalog">
        <h2 className="text-2xl font-semibold mb-4">Service Catalog</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services.map((service) => (
            <Card
              key={service.name}
              className={`cursor-pointer transition-all hover:shadow-lg ${
                selectedService?.name === service.name ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => setSelectedService(service)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{service.name}</CardTitle>
                    <Badge className={`mt-2 ${getCategoryColor(service.category)}`}>
                      {service.category}
                    </Badge>
                  </div>
                </div>
                <CardDescription className="mt-2">{service.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <div className="text-sm font-semibold mb-1">Primary Responsibilities</div>
                  <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1">
                    {service.responsibilities.map((resp, idx) => (
                      <li key={idx}>{resp}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-sm font-semibold mb-1">Integrations</div>
                  <div className="flex flex-wrap gap-1">
                    {service.integrations.map((int, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {int}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-semibold mb-1">Observability Hooks</div>
                  <p className="text-xs text-muted-foreground">{service.observability}</p>
                </div>
                <div className="flex gap-2 pt-2 border-t">
                  {service.dashboard && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      asChild
                    >
                      <a href={service.dashboard} target="_blank" rel="noopener noreferrer">
                        Dashboard <ExternalLink className="h-3 w-3 ml-1" />
                      </a>
                    </Button>
                  )}
                  {service.repo && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      asChild
                    >
                      <a href={service.repo} target="_blank" rel="noopener noreferrer">
                        Repo <ExternalLink className="h-3 w-3 ml-1" />
                      </a>
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Product Lifecycle Flow */}
      <Card>
        <CardHeader>
          <CardTitle>Product Lifecycle Flow</CardTitle>
          <CardDescription>How a product/order moves through the system</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {lifecycleSteps.map((step, idx) => (
              <div key={step.step} className="flex items-start gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                  {step.step}
                </div>
                <div className="flex-1">
                  <div className="font-semibold mb-2">{step.name}</div>
                  <div className="flex flex-wrap gap-2">
                    {step.systems.map((system) => (
                      <Badge key={system} variant="outline">
                        {system}
                      </Badge>
                    ))}
                  </div>
                </div>
                {idx < lifecycleSteps.length - 1 && (
                  <div className="absolute left-4 top-12 w-0.5 h-8 bg-primary/30" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Observability Touchpoints */}
      <Card>
        <CardHeader>
          <CardTitle>Observability Touchpoints</CardTitle>
          <CardDescription>How telemetry flows through the observability stack</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg border bg-card">
                <div className="font-semibold mb-2 flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Alloy Agents
                </div>
                <p className="text-sm text-muted-foreground">
                  Run on MDSO host, tail log files, export OTLP
                </p>
              </div>
              <div className="p-4 rounded-lg border bg-card">
                <div className="font-semibold mb-2 flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  OTEL Emitters
                </div>
                <p className="text-sm text-muted-foreground">
                  Sense apps instrumented with OTel SDK
                </p>
              </div>
              <div className="p-4 rounded-lg border bg-card">
                <div className="font-semibold mb-2 flex items-center gap-2">
                  <Network className="h-4 w-4" />
                  Correlation Engine
                </div>
                <p className="text-sm text-muted-foreground">
                  Correlates, enriches, compacts telemetry
                </p>
              </div>
              <div className="p-4 rounded-lg border bg-card">
                <div className="font-semibold mb-2 flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Data Stores
                </div>
                <p className="text-sm text-muted-foreground">
                  Loki, Tempo, Prometheus, Pyroscope
                </p>
              </div>
            </div>
            <div className="pt-4 border-t">
              <Button variant="outline" asChild>
                <a href="/docs#observability-touchpoints">View detailed documentation</a>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Strategic Applications */}
      <Card>
        <CardHeader>
          <CardTitle>Strategic Applications</CardTitle>
          <CardDescription>Moonshot, Titan, Temple, Galaxy - Key web applications</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {['Moonshot', 'Titan', 'Temple', 'Galaxy'].map((app) => {
              const service = services.find((s) => s.name === app)
              return (
                <Card key={app} className="bg-muted/50">
                  <CardHeader>
                    <CardTitle className="text-lg">{app}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">{service?.description}</p>
                    <div>
                      <div className="text-sm font-semibold mb-2">Where it sits:</div>
                      <p className="text-xs text-muted-foreground">
                        Web application layer, integrates with Kong API Gateway and MDSO for service
                        orchestration. Emits application logs and API traces to the observability stack.
                      </p>
                    </div>
                    <div className="mt-3">
                      <div className="text-sm font-semibold mb-2">Observability Integration:</div>
                      <p className="text-xs text-muted-foreground">
                        Application logs collected via Alloy agent or direct OTLP export. API traces
                        captured through Kong gateway instrumentation. Metrics available in Prometheus.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
