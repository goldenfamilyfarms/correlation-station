import { useState } from 'react'
import { ExternalLink, BarChart3, Activity, Dog, Flame, TestTube, Globe } from 'lucide-react'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export default function HomePage() {
  const [dataDogModalOpen, setDataDogModalOpen] = useState(false)

  const quickLinks = [
    {
      title: 'Grafana Dashboard',
      description: 'Access the Grafana UI for logs, traces, and metrics visualization',
      icon: BarChart3,
      color: 'grafana-orange',
      href: 'http://austx-mdso-logs-02.chtrse.com/grafana/',
      external: true,
    },
    {
      title: 'Correlation Engine',
      description: 'View correlation engine metrics and API documentation',
      icon: Activity,
      color: 'grafana-blue',
      href: 'http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs',
      external: true,
    },
    {
      title: 'Pyroscope',
      description: 'Continuous profiling for performance analysis',
      icon: Flame,
      color: 'grafana-yellow',
      href: 'http://austx-mdso-logs-02.chtrse.com/pyroscope',
      external: true,
    },
    {
      title: 'Prometheus',
      description: 'Metrics storage and querying',
      icon: TestTube,
      color: 'grafana-red',
      href: 'http://austx-mdso-logs-02.chtrse.com/prometheus/',
      external: true,
    },
  ]

  const handleDataDogClick = () => {
    setDataDogModalOpen(true)
  }

  const handleConfirmDataDog = () => {
    window.open('https://app.datadoghq.com', '_blank')
    setDataDogModalOpen(false)
  }

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4">
        <h1 className="text-5xl font-bold text-gray-900">
          Welcome to <span className="text-grafana-orange">Correlation Station</span>
        </h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Your central hub for observability and monitoring training. Learn how to use Grafana,
          OpenTelemetry, TraceQL, PromQL, and master distributed systems observability.
        </p>
      </div>

      {/* Quick Links Section */}
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-4">Quick Access</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {quickLinks.map((link) => {
            const Icon = link.icon
            return (
              <Card
                key={link.title}
                className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-grafana-orange"
                onClick={() => window.open(link.href, '_blank')}
              >
                <CardHeader>
                  <div className={`w-12 h-12 rounded-lg bg-${link.color}/10 flex items-center justify-center mb-3`}>
                    <Icon className={`h-6 w-6 text-${link.color}`} style={{ color: `var(--tw-${link.color})` }} />
                  </div>
                  <CardTitle className="flex items-center gap-2">
                    {link.title}
                    {link.external && <ExternalLink className="h-4 w-4 text-gray-400" />}
                  </CardTitle>
                  <CardDescription>{link.description}</CardDescription>
                </CardHeader>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Legacy Tools Section */}
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-4">Legacy Tools</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card
            className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-gray-400"
            onClick={handleDataDogClick}
          >
            <CardHeader>
              <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center mb-3">
                <Dog className="h-6 w-6 text-purple-600" />
              </div>
              <CardTitle className="flex items-center gap-2">
                DataDog
                <ExternalLink className="h-4 w-4 text-gray-400" />
              </CardTitle>
              <CardDescription>
                The old observability platform (click if you dare...)
              </CardDescription>
            </CardHeader>
          </Card>

          <Card
            className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-grafana-blue"
            onClick={() => window.open('http://austx-mdso-logs-02.chtrse.com/', '_blank')}
          >
            <CardHeader>
              <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center mb-3">
                <Globe className="h-6 w-6 text-blue-600" />
              </div>
              <CardTitle className="flex items-center gap-2">
                Meta Web Tool
                <ExternalLink className="h-4 w-4 text-gray-400" />
              </CardTitle>
              <CardDescription>
                Access the main MDSO web portal and tools
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>

      {/* Learning Resources */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-2xl font-semibold text-gray-900 mb-4">Getting Started</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="font-semibold text-grafana-orange mb-2">Documentation</h3>
            <p className="text-sm text-gray-600">
              Explore comprehensive guides on TraceQL, PromQL, and application instrumentation
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-grafana-blue mb-2">Architecture</h3>
            <p className="text-sm text-gray-600">
              Learn about our distributed systems architecture and design patterns
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-grafana-green mb-2">SECA Reviews</h3>
            <p className="text-sm text-gray-600">
              Bi-weekly error analysis and resolution tracking for production issues
            </p>
          </div>
        </div>
      </div>

      {/* DataDog Modal with Tim Robinson Meme */}
      <Dialog open={dataDogModalOpen} onOpenChange={setDataDogModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-2xl">Hold up!</DialogTitle>
            <DialogDescription className="text-center">
              Are you sure you want to use DataDog?
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col items-center gap-4 py-4">
            {/* Tim Robinson "Are you sure about that?" Meme */}
            <div className="w-full bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg p-8 border-2 border-blue-200">
              <div className="text-center space-y-4">
                <div className="text-6xl">🤔</div>
                <div className="text-3xl font-bold text-blue-600">ARE YOU SURE</div>
                <div className="text-3xl font-bold text-purple-600">ABOUT THAT?!</div>
                <div className="text-sm text-gray-600 italic mt-4">
                  (Tim Robinson would be disappointed)
                </div>
              </div>
            </div>

            <p className="text-center text-sm text-gray-600">
              We have all these cool open-source observability tools...
            </p>
          </div>

          <DialogFooter className="flex-col sm:flex-col gap-2">
            <Button
              variant="destructive"
              onClick={handleConfirmDataDog}
              className="w-full"
            >
              Yes, I'm sure (take me to DataDog)
            </Button>
            <Button
              variant="default"
              onClick={() => setDataDogModalOpen(false)}
              className="w-full bg-grafana-orange hover:bg-grafana-orange/90"
            >
              No, I'm sorry! I like cool OM tools
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
