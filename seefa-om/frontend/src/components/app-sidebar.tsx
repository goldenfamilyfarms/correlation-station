import * as React from "react"
import {
  Home,
  BookOpen,
  Network,
  AlertCircle,
  GraduationCap,
  BarChart3,
  Activity,
  Flame,
  Gauge,
  FileText,
  ExternalLink,
  Database,
  Bug,
  Calendar,
  Shield,
  Code,
} from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth"
import LoginModal from "./LoginModal"
import { cn } from "@/lib/utils"

export function AppSidebar() {
  const location = useLocation()
  const { isAuthenticated, user } = useAuth()
  const [loginOpen, setLoginOpen] = React.useState(false)

  const grafanaItems = [
    {
      title: "Grafana Stack",
      url: "/docs",
      icon: BarChart3,
    },
    {
      title: "OpenTelemetry",
      url: "/docs",
      icon: Activity,
    },
    {
      title: "Query Languages",
      url: "/docs",
      icon: Code,
    },
  ]

  const complianceItems = [
    {
      title: "SECA Review",
      url: "/seca-review",
      icon: AlertCircle,
    },
    {
      title: "Compliance Team",
      url: "/compliance",
      icon: Shield,
    },
  ]

  const overviewItems = [
    {
      title: "Home",
      url: "/",
      icon: Home,
    },
    {
      title: "SEEFA Architecture",
      url: "/architecture",
      icon: Network,
    },
    {
      title: "NetDev101",
      url: "/netdev101",
      icon: GraduationCap,
    },
  ]

  const toolsItems = [
    {
      title: "Grafana Dashboard",
      url: "http://159.56.4.94:3000",
      icon: BarChart3,
      external: true,
    },
    {
      title: "Correlation Engine",
      url: "/correlation-engine",
      icon: Activity,
      external: false,
    },
    {
      title: "Pyroscope",
      url: "http://159.56.4.94:4040",
      icon: Flame,
      external: true,
    },
    {
      title: "Prometheus",
      url: "http://159.56.4.94:9090",
      icon: Gauge,
      external: true,
    },
  ]

  const handleExternalClick = (url: string, e: React.MouseEvent) => {
    e.preventDefault()
    window.open(url, "_blank", "noopener,noreferrer")
  }

  const NavItem = ({ item, isActive }: { item: any; isActive: boolean }) => {
    const Icon = item.icon
    const baseClasses = "flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-all duration-200 rounded-md"
    const activeClasses = isActive 
      ? "bg-white/10 text-white border-l-2 border-primary" 
      : "text-white/70 hover:bg-white/5 hover:text-white"
    
    if (item.external) {
      return (
        <button
          onClick={(e) => handleExternalClick(item.url, e)}
          className={cn(baseClasses, activeClasses, "w-full text-left")}
        >
          <Icon className="h-4 w-4" />
          <span>{item.title}</span>
          <ExternalLink className="ml-auto h-3 w-3 opacity-60" />
        </button>
      )
    }

    return (
      <Link
        to={item.url}
        className={cn(baseClasses, activeClasses, "w-full")}
      >
        <Icon className="h-4 w-4" />
        <span>{item.title}</span>
      </Link>
    )
  }

  return (
    <>
      <aside className="w-64 bg-[#1E1F20] border-r border-white/10 text-white overflow-y-auto flex flex-col" style={{ backgroundColor: '#1E1F20' }}>
        <div className="flex-1 p-4 space-y-6">
          {/* Grafana Stack Section */}
          <div>
            <h3 className="px-4 mb-2 text-xs font-semibold text-white/50 uppercase tracking-wider">Grafana Stack</h3>
            <nav className="space-y-1">
              {grafanaItems.map((item) => {
                const isActive = location.pathname === item.url
                return (
                  <NavItem key={item.title} item={item} isActive={isActive} />
                )
              })}
            </nav>
          </div>

          {/* Compliance/SECA Section */}
          <div>
            <h3 className="px-4 mb-2 text-xs font-semibold text-white/50 uppercase tracking-wider">Compliance & SECA</h3>
            <nav className="space-y-1">
              {complianceItems.map((item) => {
                const isActive = location.pathname === item.url
                return (
                  <NavItem key={item.title} item={item} isActive={isActive} />
                )
              })}
            </nav>
          </div>

          {/* Overview Section */}
          <div>
            <h3 className="px-4 mb-2 text-xs font-semibold text-white/50 uppercase tracking-wider">Overview</h3>
            <nav className="space-y-1">
              {overviewItems.map((item) => {
                const isActive = location.pathname === item.url
                return (
                  <NavItem key={item.title} item={item} isActive={isActive} />
                )
              })}
            </nav>
          </div>

          {/* Tools Section */}
          <div>
            <h3 className="px-4 mb-2 text-xs font-semibold text-white/50 uppercase tracking-wider">Tools</h3>
            <nav className="space-y-1">
              {toolsItems.map((item) => {
                const isActive = !item.external && location.pathname === item.url
                return (
                  <NavItem key={item.title} item={item} isActive={isActive} />
                )
              })}
            </nav>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/10">
          {isAuthenticated ? (
            <div className="flex items-center gap-2 px-2">
              <div className="flex flex-col flex-1 min-w-0">
                <span className="text-sm font-medium truncate text-white">{user?.username}</span>
                <span className="text-xs text-white/50 truncate">Logged in</span>
              </div>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="w-full bg-white/5 border-white/20 text-white hover:bg-white/10"
              onClick={() => setLoginOpen(true)}
            >
              Login
            </Button>
          )}
        </div>
      </aside>
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  )
}
