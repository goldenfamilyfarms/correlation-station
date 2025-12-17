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
} from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth"
import LoginModal from "./LoginModal"

export function AppSidebar() {
  const location = useLocation()
  const { isAuthenticated, user } = useAuth()
  const [loginOpen, setLoginOpen] = React.useState(false)

  const overviewItems = [
    {
      title: "Home",
      url: "/",
      icon: Home,
    },
    {
      title: "Documentation",
      url: "/docs",
      icon: BookOpen,
    },
    {
      title: "SEEFA Architecture",
      url: "/architecture",
      icon: Network,
    },
    {
      title: "SECA Review",
      url: "/seca-review",
      icon: AlertCircle,
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
    {
      title: "Meta Web Tool",
      url: "http://159.56.4.94/reports",
      icon: FileText,
      external: true,
    },
    {
      title: "Datadog",
      url: "#",
      icon: Database,
      external: false,
      isModal: true,
    },
  ]

  const learningItems = [
    {
      title: "Learning Path",
      url: "/netdev101",
      icon: GraduationCap,
    },
    {
      title: "Error Reports",
      url: "/seca-review",
      icon: Bug,
    },
    {
      title: "Weekly Automation Errors",
      url: "/seca-review",
      icon: Calendar,
    },
  ]

  const handleDatadogClick = (e: React.MouseEvent) => {
    e.preventDefault()
    // TODO: Open Datadog confirmation modal
    alert("Datadog modal - coming soon")
  }

  const handleExternalClick = (url: string, e: React.MouseEvent) => {
    e.preventDefault()
    window.open(url, "_blank", "noopener,noreferrer")
  }

  return (
    <Sidebar variant="inset">
      <SidebarHeader className="border-b border-border/50 bg-gradient-to-r from-transparent via-primary/5 to-transparent">
        <div className="flex items-center gap-3 px-2 py-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg shadow-primary/20 hover:scale-110 transition-transform duration-300 relative overflow-hidden group/logo">
            <div className="absolute inset-0 bg-gradient-to-br from-accent/30 to-transparent opacity-0 group-hover/logo:opacity-100 transition-opacity duration-300" />
            <Activity className="h-5 w-5 relative z-10" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text">Correlation Station</span>
            <span className="text-xs text-muted-foreground">Observability & Automation Hub</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Overview</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {overviewItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.url
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={isActive}
                      className="transition-all duration-300 hover:bg-primary/10 hover:translate-x-1 data-[active=true]:bg-primary/15 data-[active=true]:border-l-2 data-[active=true]:border-primary"
                    >
                      <Link to={item.url}>
                        <Icon className="h-4 w-4" />
                        <span className="font-medium">{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>Tools</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {toolsItems.map((item) => {
                const Icon = item.icon
                const isActive = !item.external && location.pathname === item.url
                return (
                  <SidebarMenuItem key={item.title}>
                    {item.isModal ? (
                      <SidebarMenuButton 
                        onClick={handleDatadogClick} 
                        isActive={isActive}
                        className="transition-all duration-300 hover:bg-primary/10 hover:translate-x-1 data-[active=true]:bg-primary/15 data-[active=true]:border-l-2 data-[active=true]:border-primary"
                      >
                        <Icon className="h-4 w-4" />
                        <span className="font-medium">{item.title}</span>
                      </SidebarMenuButton>
                    ) : item.external ? (
                      <SidebarMenuButton 
                        onClick={(e) => handleExternalClick(item.url, e)} 
                        isActive={isActive}
                        className="transition-all duration-300 hover:bg-primary/10 hover:translate-x-1 data-[active=true]:bg-primary/15 data-[active=true]:border-l-2 data-[active=true]:border-primary"
                      >
                        <Icon className="h-4 w-4" />
                        <span className="font-medium">{item.title}</span>
                        <ExternalLink className="ml-auto h-3 w-3 opacity-60" />
                      </SidebarMenuButton>
                    ) : (
                      <SidebarMenuButton 
                        asChild 
                        isActive={isActive}
                        className="transition-all duration-300 hover:bg-primary/10 hover:translate-x-1 data-[active=true]:bg-primary/15 data-[active=true]:border-l-2 data-[active=true]:border-primary"
                      >
                        <Link to={item.url}>
                          <Icon className="h-4 w-4" />
                          <span className="font-medium">{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    )}
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>Learning & Quality</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {learningItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.url
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild 
                      isActive={isActive}
                      className="transition-all duration-300 hover:bg-primary/10 hover:translate-x-1 data-[active=true]:bg-primary/15 data-[active=true]:border-l-2 data-[active=true]:border-primary"
                    >
                      <Link to={item.url}>
                        <Icon className="h-4 w-4" />
                        <span className="font-medium">{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-border/50 bg-gradient-to-r from-transparent via-primary/5 to-transparent">
        {isAuthenticated ? (
          <div className="flex items-center gap-2 px-2">
            <div className="flex flex-col flex-1 min-w-0">
              <span className="text-sm font-medium truncate">{user?.username}</span>
              <span className="text-xs text-muted-foreground truncate">Logged in</span>
            </div>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => setLoginOpen(true)}
          >
            Login
          </Button>
        )}
      </SidebarFooter>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </Sidebar>
  )
}

