import { useState } from 'react'
import { BarChart3, Activity, Flame, Gauge, Users, TrendingUp, BookOpen, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { QuickLinkCard } from '@/components/QuickLinkCard'
import { KpiCard } from '@/components/KpiCard'
import { HealthRow } from '@/components/HealthRow'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { Link } from 'react-router-dom'

// Mock data - TODO: Replace with API calls
const weeklyErrorData = [
  { week: 'Week 1', provisioning: 12, compliance: 8, other: 5 },
  { week: 'Week 2', provisioning: 15, compliance: 10, other: 7 },
  { week: 'Week 3', provisioning: 8, compliance: 6, other: 4 },
  { week: 'Week 4', provisioning: 10, compliance: 9, other: 6 },
]

const learningPathSteps = [
  { id: 1, title: 'Getting started with Grafana', status: 'completed' },
  { id: 2, title: 'Logs & Traces (Loki/Tempo)', status: 'in_progress' },
  { id: 3, title: 'Metrics & Prometheus', status: 'not_started' },
  { id: 4, title: 'Code Profiling with Pyroscope', status: 'not_started' },
  { id: 5, title: 'Automation Deep Dives', status: 'not_started' },
]

const recentErrors = [
  { service: 'ARDA', type: 'Timeout', severity: 'High', status: 'Open', owner: 'John D.', link: '#' },
  { service: 'BEORN', type: 'Parse Error', severity: 'Medium', status: 'Triage', owner: 'Jane S.', link: '#' },
  { service: 'PALANTIR', type: 'Upstream 5xx', severity: 'High', status: 'Open', owner: 'Bob M.', link: '#' },
  { service: 'MDSO', type: 'Config Error', severity: 'Low', status: 'Resolved', owner: 'Alice K.', link: '#' },
]

const healthServices = [
  { service: 'Correlation Engine', status: 'healthy' as const, description: 'All systems operational' },
  { service: 'Grafana Stack', status: 'healthy' as const, description: 'Loki, Tempo, Prometheus running' },
  { service: 'Redis Cache', status: 'partial' as const, description: 'High memory usage' },
  { service: 'MDSO Alloy Agent', status: 'healthy' as const, description: 'Collecting telemetry' },
  { service: 'Sense Apps', status: 'limited' as const, description: 'Some endpoints degraded' },
]

export default function HomePage() {
  const [dataDogModalOpen, setDataDogModalOpen] = useState(false)

  const handleConfirmDataDog = () => {
    window.open('https://app.datadoghq.com', '_blank', 'noopener,noreferrer')
    setDataDogModalOpen(false)
  }

  return (
    <div className="flex flex-1 flex-col gap-6 animate-in fade-in-50 duration-700">
      {/* Band 1 - Quick Access Cards */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-1 w-12 bg-gradient-to-r from-primary to-accent rounded-full" />
          <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
            Quick Access
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickLinkCard
            title="Grafana Dashboard"
            description="Access the Grafana UI for logs, traces, and metrics visualization"
            icon={BarChart3}
            href="http://159.56.4.94:3000"
            external
          />
          <QuickLinkCard
            title="Correlation Engine"
            description="View correlation engine metrics and health status"
            icon={Activity}
            href="/correlation-engine"
          />
          <QuickLinkCard
            title="Pyroscope"
            description="Continuous profiling for performance analysis"
            icon={Flame}
            href="http://159.56.4.94:4040"
            external
          />
          <QuickLinkCard
            title="Prometheus"
            description="Metrics storage and querying"
            icon={Gauge}
            href="http://159.56.4.94:9090"
            external
          />
        </div>
      </div>

      {/* Band 2 - Learning KPIs */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-1 w-12 bg-gradient-to-r from-primary to-accent rounded-full" />
          <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
            Learning KPIs
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            title="Onboarded Engineers"
            value={18}
            description="completed observability bootcamp"
            icon={Users}
          />
          <KpiCard
            title="Loki/Tempo Proficiency"
            value="72%"
            description="passed log & trace quiz"
            icon={TrendingUp}
            trend={{ value: 5, label: 'vs last month', positive: true }}
          />
          <KpiCard
            title="MTTD Improvement"
            value="35%"
            description="reduction vs last quarter"
            icon={TrendingUp}
            trend={{ value: 12, label: 'points', positive: true }}
          />
          <KpiCard
            title="Playbooks Covered"
            value="14 / 20"
            description="SRE runbooks with dashboards"
            icon={BookOpen}
          />
        </div>
      </div>

      {/* Band 3 - Chart + Learning Path (2/3 + 1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left (2/3) - Weekly Automation Errors Chart */}
        <Card className="lg:col-span-2 hover:shadow-xl transition-all duration-500 border border-border/50 bg-gradient-to-br from-card to-card/95 backdrop-blur-sm group">
          <CardHeader className="border-b border-border/50 bg-gradient-to-r from-transparent via-primary/5 to-transparent">
            <CardTitle className="text-xl font-bold">Weekly Automation Errors</CardTitle>
            <CardDescription className="text-sm">Error counts over the last 4 weeks</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={weeklyErrorData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="provisioning" stackId="1" stroke="#316CB8" fill="#316CB8" fillOpacity={0.6} />
                <Area type="monotone" dataKey="compliance" stackId="1" stroke="#4DB6AC" fill="#4DB6AC" fillOpacity={0.6} />
                <Area type="monotone" dataKey="other" stackId="1" stroke="#E0E0E0" fill="#E0E0E0" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-[#316CB8]" />
                <span>Provisioning Failures</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-[#4DB6AC]" />
                <span>Compliance Failures</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-[#E0E0E0]" />
                <span>Other</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right (1/3) - Your Learning Path */}
        <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 bg-gradient-to-br from-card to-card/95 backdrop-blur-sm group">
          <CardHeader className="border-b border-border/50 bg-gradient-to-r from-transparent via-accent/5 to-transparent">
            <CardTitle className="text-xl font-bold">Your Learning Path</CardTitle>
            <CardDescription className="text-sm">Track your progress</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-3">
              {learningPathSteps.map((step, idx) => (
                <div 
                  key={step.id} 
                  className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/50 transition-all duration-200 group/step border border-transparent hover:border-border/50"
                  style={{ animationDelay: `${idx * 100}ms` }}
                >
                  <div className="flex-shrink-0 mt-0.5 relative">
                    {step.status === 'completed' ? (
                      <div className="relative">
                        <CheckCircle2 className="h-6 w-6 text-green-500 group-hover/step:scale-110 transition-transform duration-200" />
                        <div className="absolute inset-0 bg-green-500/20 rounded-full blur-md opacity-0 group-hover/step:opacity-100 transition-opacity duration-200" />
                      </div>
                    ) : step.status === 'in_progress' ? (
                      <div className="relative">
                        <div className="h-6 w-6 rounded-full border-2 border-primary border-t-transparent animate-spin group-hover/step:scale-110 transition-transform duration-200" />
                        <div className="absolute inset-0 bg-primary/20 rounded-full blur-md opacity-50" />
                      </div>
                    ) : (
                      <div className="relative">
                        <div className="h-6 w-6 rounded-full border-2 border-muted-foreground group-hover/step:border-primary/50 transition-colors duration-200" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-foreground group-hover/step:text-primary transition-colors duration-200">
                      {step.title}
                    </div>
                    <div className="text-xs text-muted-foreground capitalize mt-0.5 group-hover/step:text-foreground/70 transition-colors duration-200">
                      {step.status.replace('_', ' ')}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4" asChild>
              <Link to="/netdev101">View Full Path</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Band 4 - Error Reports + Health Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left (2/3) - Latest Error Reports */}
        <Card className="lg:col-span-2 hover:shadow-xl transition-all duration-500 border border-border/50 bg-gradient-to-br from-card to-card/95 backdrop-blur-sm group">
          <CardHeader className="border-b border-border/50 bg-gradient-to-r from-transparent via-primary/5 to-transparent">
            <CardTitle className="text-xl font-bold">Latest Error Reports</CardTitle>
            <CardDescription className="text-sm">Recent internal error records</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-0">
              <div className="grid grid-cols-6 gap-4 pb-3 border-b border-border/50 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                <div>Service</div>
                <div>Type</div>
                <div>Severity</div>
                <div>Status</div>
                <div>Owner</div>
                <div>Link</div>
              </div>
              {recentErrors.map((error, idx) => (
                <div 
                  key={idx} 
                  className="grid grid-cols-6 gap-4 py-3 border-b border-border/30 last:border-0 text-sm hover:bg-muted/30 transition-colors duration-200 rounded-md px-2 group/row"
                >
                  <div className="font-semibold text-foreground group-hover/row:text-primary transition-colors">{error.service}</div>
                  <div className="text-muted-foreground">{error.type}</div>
                  <div>
                    <span className={`px-2.5 py-1 rounded-md text-xs font-semibold shadow-sm ${
                      error.severity === 'High' ? 'bg-red-500/20 text-red-600 border border-red-500/30' :
                      error.severity === 'Medium' ? 'bg-yellow-500/20 text-yellow-600 border border-yellow-500/30' :
                      'bg-green-500/20 text-green-600 border border-green-500/30'
                    }`}>
                      {error.severity}
                    </span>
                  </div>
                  <div className="text-muted-foreground">{error.status}</div>
                  <div className="text-muted-foreground">{error.owner}</div>
                  <div>
                    <a 
                      href={error.link} 
                      className="text-primary hover:text-accent hover:underline font-medium transition-colors duration-200 inline-flex items-center gap-1"
                    >
                      View
                      <span className="opacity-0 group-hover/row:opacity-100 transition-opacity">→</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4" asChild>
              <Link to="/seca-review">View All Errors</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Right (1/3) - Automation Health Snapshot */}
        <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 bg-gradient-to-br from-card to-card/95 backdrop-blur-sm group">
          <CardHeader className="border-b border-border/50 bg-gradient-to-r from-transparent via-accent/5 to-transparent">
            <CardTitle className="text-xl font-bold">Automation Health Snapshot</CardTitle>
            <CardDescription className="text-sm">Service status overview</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-0">
              {healthServices.map((service, idx) => (
                <HealthRow
                  key={idx}
                  service={service.service}
                  status={service.status}
                  description={service.description}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Datadog Confirmation Modal */}
      <Dialog open={dataDogModalOpen} onOpenChange={setDataDogModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Leave Correlation Station?</DialogTitle>
            <DialogDescription>
              You're about to leave our open-source observability stack and go to Datadog.
              Are you sure you want to continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="destructive"
              onClick={handleConfirmDataDog}
              className="w-full sm:w-auto"
            >
              Yes, take me to Datadog
            </Button>
            <Button
              variant="default"
              onClick={() => setDataDogModalOpen(false)}
              className="w-full sm:w-auto"
            >
              No, keep me in Correlation Station
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
