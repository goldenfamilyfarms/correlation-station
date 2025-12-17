import { useState } from 'react'
import { BarChart3, Activity, Shield, BookOpen, Code, Network, ChevronLeft, ChevronRight, ExternalLink, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

const carouselSections = [
  {
    id: 'grafana',
    title: 'Grafana Stack & Observability',
    description: 'Learn and master the Grafana observability stack including Loki, Tempo, Prometheus, and Pyroscope. Master distributed systems observability with OpenTelemetry.',
    icon: BarChart3,
    color: 'from-blue-500/20 to-cyan-500/20',
    borderColor: 'border-blue-500/30',
    items: [
      { title: 'Grafana Dashboards', description: 'Access unified dashboards for logs, traces, and metrics', link: '/docs' },
      { title: 'Query Languages', description: 'Master LogQL, TraceQL, and PromQL', link: '/docs' },
      { title: 'OpenTelemetry', description: 'Learn distributed tracing and instrumentation', link: '/docs' },
      { title: 'Correlation Engine', description: 'Understand our correlation and processing pipeline', link: '/correlation-engine' },
    ]
  },
  {
    id: 'compliance',
    title: 'Compliance & SECA Team',
    description: 'Resources and tools for the Compliance workstream. Network Compliance, Network Acceptance, and automation support for Spectrum Business boundary partners.',
    icon: Shield,
    color: 'from-orange-500/20 to-red-500/20',
    borderColor: 'border-orange-500/30',
    items: [
      { title: 'SECA Review', description: 'Review and analyze SECA automation errors', link: '/seca-review' },
      { title: 'Compliance Team', description: 'Team resources, standards, and documentation', link: '/compliance' },
      { title: 'MDSO Products', description: 'Service Mapper, Disconnect Mapper, WIA Mapper', link: '/compliance' },
      { title: 'SEnSE Microservices', description: 'Palantir and Beorn compliance endpoints', link: '/compliance' },
    ]
  },
  {
    id: 'architecture',
    title: 'SEEFA Architecture',
    description: 'Understand the architecture, design decisions, and technical implementation of our observability and automation platform.',
    icon: Network,
    color: 'from-purple-500/20 to-pink-500/20',
    borderColor: 'border-purple-500/30',
    items: [
      { title: 'System Architecture', description: 'High-level system design and components', link: '/architecture' },
      { title: 'Data Flow', description: 'How data moves through our systems', link: '/architecture' },
      { title: 'Deployment Guide', description: 'Deployment and scaling strategies', link: '/architecture' },
      { title: 'Best Practices', description: 'Development and operational standards', link: '/architecture' },
    ]
  },
  {
    id: 'learning',
    title: 'Learning & Development',
    description: 'Onboarding resources, tutorials, and learning paths for engineers new to observability and our platform.',
    icon: BookOpen,
    color: 'from-green-500/20 to-emerald-500/20',
    borderColor: 'border-green-500/30',
    items: [
      { title: 'NetDev101', description: 'Learning path for network developers', link: '/netdev101' },
      { title: 'Getting Started', description: 'Quick start guides and tutorials', link: '/docs' },
      { title: 'Code Examples', description: 'Sample code and implementations', link: '/docs' },
      { title: 'Team Onboarding', description: 'Resources for new team members', link: '/docs' },
    ]
  },
]

export default function HomePage() {
  const [currentSection, setCurrentSection] = useState(0)

  const nextSection = () => {
    setCurrentSection((prev) => (prev + 1) % carouselSections.length)
  }

  const prevSection = () => {
    setCurrentSection((prev) => (prev - 1 + carouselSections.length) % carouselSections.length)
  }

  const current = carouselSections[currentSection]
  const Icon = current.icon

  return (
    <div className="flex flex-1 flex-col gap-8 animate-in fade-in-50 duration-700">
      {/* Welcome Header */}
      <div className="space-y-4">
        <div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-4 bg-gradient-to-r from-foreground via-foreground/90 to-foreground/70 bg-clip-text">
            Welcome to Correlation Station
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground max-w-4xl leading-relaxed">
            Your central hub for observability and monitoring. Learn how to use Grafana, OpenTelemetry, TraceQL, PromQL, LogQL, and master distributed systems observability.
          </p>
        </div>
      </div>

      {/* Carousel Section */}
      <div className="relative">
        <Card className="overflow-hidden border-2 hover:shadow-2xl transition-all duration-500 bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
          <CardHeader className={`bg-gradient-to-r ${current.color} border-b ${current.borderColor} pb-4`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl bg-gradient-to-br ${current.color} border ${current.borderColor}`}>
                  <Icon className="h-8 w-8 text-foreground" />
                </div>
                <div>
                  <CardTitle className="text-3xl font-bold mb-2">{current.title}</CardTitle>
                  <CardDescription className="text-base max-w-2xl">{current.description}</CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={prevSection}
                  className="h-10 w-10 rounded-full"
                >
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <div className="flex gap-1.5">
                  {carouselSections.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentSection(idx)}
                      className={`h-2 rounded-full transition-all duration-300 ${
                        idx === currentSection ? 'w-8 bg-primary' : 'w-2 bg-muted-foreground/30'
                      }`}
                    />
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={nextSection}
                  className="h-10 w-10 rounded-full"
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {current.items.map((item, idx) => (
                <Link
                  key={idx}
                  to={item.link}
                  className="group"
                >
                  <Card className="hover:shadow-lg transition-all duration-300 border border-border/50 hover:border-primary/50 hover:scale-[1.02] bg-gradient-to-br from-card to-card/95">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                          {item.title}
                        </CardTitle>
                        <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <CardDescription className="text-sm leading-relaxed">
                        {item.description}
                      </CardDescription>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Access Grid */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-1 w-12 bg-gradient-to-r from-primary to-accent rounded-full" />
          <h2 className="text-3xl font-bold tracking-tight">Quick Access</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="hover:shadow-xl transition-all duration-500 cursor-pointer border border-border/50 hover:border-primary/50 hover:scale-[1.02] group relative overflow-hidden bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <CardHeader className="relative z-10">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <BarChart3 className="h-7 w-7 text-blue-600" />
              </div>
              <CardTitle className="flex items-center gap-2 text-lg group-hover:text-primary transition-colors">
                Grafana Dashboard
                <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </CardTitle>
              <CardDescription className="line-clamp-2 leading-relaxed text-sm">
                Access the Grafana UI for logs, traces, and metrics visualization
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:shadow-xl transition-all duration-500 cursor-pointer border border-border/50 hover:border-primary/50 hover:scale-[1.02] group relative overflow-hidden bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <CardHeader className="relative z-10">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <Shield className="h-7 w-7 text-orange-600" />
              </div>
              <CardTitle className="flex items-center gap-2 text-lg group-hover:text-primary transition-colors">
                SECA Review
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </CardTitle>
              <CardDescription className="line-clamp-2 leading-relaxed text-sm">
                Review and analyze SECA automation errors and compliance issues
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:shadow-xl transition-all duration-500 cursor-pointer border border-border/50 hover:border-primary/50 hover:scale-[1.02] group relative overflow-hidden bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <CardHeader className="relative z-10">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <Network className="h-7 w-7 text-purple-600" />
              </div>
              <CardTitle className="flex items-center gap-2 text-lg group-hover:text-primary transition-colors">
                Architecture
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </CardTitle>
              <CardDescription className="line-clamp-2 leading-relaxed text-sm">
                Explore the SEEFA architecture and system design
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:shadow-xl transition-all duration-500 cursor-pointer border border-border/50 hover:border-primary/50 hover:scale-[1.02] group relative overflow-hidden bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <CardHeader className="relative z-10">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <BookOpen className="h-7 w-7 text-green-600" />
              </div>
              <CardTitle className="flex items-center gap-2 text-lg group-hover:text-primary transition-colors">
                Documentation
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </CardTitle>
              <CardDescription className="line-clamp-2 leading-relaxed text-sm">
                Comprehensive guides and reference documentation
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>
    </div>
  )
}
