import { FileText, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAuth } from "@/lib/auth"

import { Activity } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAuth } from "@/lib/auth"

export function SiteHeader() {
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 backdrop-blur-md bg-[#1E1F20] shadow-lg" style={{ backgroundColor: '#1E1F20' }}>
      <div className="flex h-16 items-center justify-between px-6 text-white">
        {/* Left side - Title */}
        <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg shadow-primary/20">
            <Activity className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold leading-tight">Correlation Station</span>
            <span className="text-xs text-white/70 leading-tight">Observability & Monitoring Automation</span>
          </div>
        </Link>

        {/* Right side - API Docs and Login/User */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            asChild
            className="text-white hover:bg-white/10 hover:text-white transition-all duration-200"
          >
            <a
              href="http://159.56.4.94:8080/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2"
            >
              <FileText className="h-4 w-4" />
              <span className="hidden sm:inline font-medium">API Docs</span>
            </a>
          </Button>
          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="relative h-9 w-9 rounded-full text-white hover:bg-white/10 hover:text-white transition-all duration-200 hover:scale-110 ring-2 ring-transparent hover:ring-primary/30">
                  <Avatar className="h-9 w-9 border-2 border-white/20 hover:border-primary/50 transition-colors duration-200">
                    <AvatarFallback className="bg-gradient-to-br from-primary to-accent font-semibold">
                      {user?.username?.charAt(0).toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user?.username}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email || "user@example.com"}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button 
              variant="ghost" 
              size="sm" 
              asChild
              className="text-white hover:bg-white/10 hover:text-white transition-all duration-200"
            >
              <Link to="/login" className="flex items-center gap-2">
                <User className="h-4 w-4" />
                <span className="hidden sm:inline font-medium">Login</span>
              </Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}

