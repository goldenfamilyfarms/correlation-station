import { useState, useEffect } from 'react'
import { AlertCircle, Database, Zap } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { KpiCard } from '@/components/KpiCard'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Button } from '@/components/ui/button'
import { ExternalLink } from 'lucide-react'

// Mock data - TODO: Replace with API calls
const mockStats = {
  requestsInQueue: 42,
  throughput: 1250,
  errorRate: 2.3,
  droppedItems: 8,
  avgProcessingTime: 45,
  p95ProcessingTime: 120,
  otelSpansPerMin: 8500,
  droppedSpansLastWindow: 12,
  status: 'healthy' as const,
  lastUpdated: new Date().toISOString(),
}

const mockTrendsData = [
  { time: '00:00', requests: 1200, errors: 28 },
  { time: '00:05', requests: 1350, errors: 32 },
  { time: '00:10', requests: 1180, errors: 25 },
  { time: '00:15', requests: 1420, errors: 35 },
  { time: '00:20', requests: 1300, errors: 30 },
  { time: '00:25', requests: 1280, errors: 29 },
  { time: '00:30', requests: 1250, errors: 28 },
]

const recentIssues = [
  {
    timestamp: '2025-12-11 14:23:15',
    type: 'Timeout',
    service: 'ARDA',
    source: 'sense-apps',
    link: 'http://159.56.4.94:3000/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Tempo%22%5D',
  },
  {
    timestamp: '2025-12-11 13:45:22',
    type: 'Parse Error',
    service: 'BEORN',
    source: 'sense-apps',
    link: 'http://159.56.4.94:3000/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Loki%22%5D',
  },
  {
    timestamp: '2025-12-11 13:12:08',
    type: 'Upstream 5xx',
    service: 'MDSO',
    source: 'mdso-alloy',
    link: 'http://159.56.4.94:3000/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Tempo%22%5D',
  },
  {
    timestamp: '2025-12-11 12:58:41',
    type: 'Redis Connection',
    service: 'Correlation Engine',
    source: 'correlation-engine',
    link: 'http://159.56.4.94:3000/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Loki%22%5D',
  },
]

export default function CorrelationEnginePage() {
  const [stats] = useState(mockStats)

  // TODO: Implement polling every 15-30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      // TODO: Fetch from /correlation-engine/stats/current
      // setStats(fetchedStats)
    }, 30000) // 30 seconds

    return () => clearInterval(interval)
  }, [])

  const statusConfig = {
    healthy: { label: 'Healthy', variant: 'default' as const, className: 'bg-green-500' },
    degraded: { label: 'Degraded', variant: 'secondary' as const, className: 'bg-yellow-500' },
    down: { label: 'Down', variant: 'destructive' as const, className: 'bg-red-500' },
  }

  const status = statusConfig[stats.status]

  return (
    <div className="flex flex-1 flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Correlation Engine</h1>
          <p className="text-muted-foreground mt-1">
            Real-time health snapshot for the correlation service
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant={status.variant} className={status.className}>
            {status.label}
          </Badge>
          <div className="text-sm text-muted-foreground">
            Last updated: {new Date(stats.lastUpdated).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Section A - Core Stats */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Core Stats</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            title="Requests in Queue"
            value={stats.requestsInQueue}
            description="Currently queued"
            icon={Database}
          />
          <KpiCard
            title="Throughput"
            value={`${stats.throughput.toLocaleString()}/s`}
            description="Events per second"
            icon={Zap}
          />
          <KpiCard
            title="Error Rate"
            value={`${stats.errorRate}%`}
            description="Percentage of failed requests"
            icon={AlertCircle}
            trend={{ value: 0.2, label: 'vs last hour', positive: false }}
          />
          <KpiCard
            title="Dropped Items"
            value={stats.droppedItems}
            description="Items dropped in last window"
            icon={AlertCircle}
          />
        </div>
      </div>

      {/* Section B - Trends & Latency */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left - Requests & Errors Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Requests & Errors (Last 30 min)</CardTitle>
            <CardDescription>Request and error rates over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockTrendsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="requests"
                  stroke="#316CB8"
                  name="Requests/min"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="errors"
                  stroke="#F44336"
                  name="Errors/min"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Right - Latency / OTel Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>Latency & OTel Metrics</CardTitle>
            <CardDescription>Processing performance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Avg Processing Time</span>
                <span className="text-lg font-semibold">{stats.avgProcessingTime}ms</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary"
                  style={{ width: `${(stats.avgProcessingTime / 200) * 100}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">P95 Processing Time</span>
                <span className="text-lg font-semibold">{stats.p95ProcessingTime}ms</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent"
                  style={{ width: `${(stats.p95ProcessingTime / 200) * 100}%` }}
                />
              </div>
            </div>
            <div className="pt-4 border-t">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">OTEL Spans/min</span>
                <span className="text-lg font-semibold">{stats.otelSpansPerMin.toLocaleString()}</span>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Dropped Spans</span>
                <span className="text-lg font-semibold text-destructive">
                  {stats.droppedSpansLastWindow}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section C - Recent Issues */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Issues</CardTitle>
          <CardDescription>Last N issues detected by the correlation engine</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <div className="grid grid-cols-5 gap-4 pb-2 border-b text-sm font-medium text-muted-foreground">
              <div>Timestamp</div>
              <div>Type</div>
              <div>Service / Source</div>
              <div>Source</div>
              <div>Link</div>
            </div>
            {recentIssues.map((issue, idx) => (
              <div key={idx} className="grid grid-cols-5 gap-4 py-3 border-b last:border-0 text-sm">
                <div className="text-muted-foreground">{issue.timestamp}</div>
                <div>
                  <Badge variant="outline" className="bg-yellow-500/20 text-yellow-500">
                    {issue.type}
                  </Badge>
                </div>
                <div className="font-medium">{issue.service}</div>
                <div className="text-muted-foreground">{issue.source}</div>
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="h-7"
                  >
                    <a
                      href={issue.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1"
                    >
                      View
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* API Endpoints Info */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-sm">API Endpoints</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-xs text-muted-foreground space-y-1">
            <div>• <code className="bg-background px-1 rounded">GET /correlation-engine/health</code> - Health check</div>
            <div>• <code className="bg-background px-1 rounded">GET /correlation-engine/stats/current</code> - Current stats</div>
            <div>• <code className="bg-background px-1 rounded">GET /correlation-engine/stats/timeseries</code> - Time series data</div>
            <div>• <code className="bg-background px-1 rounded">GET /correlation-engine/incidents/recent</code> - Recent incidents</div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

