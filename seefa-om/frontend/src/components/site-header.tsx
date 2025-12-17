import { Search, FileText, User } from "lucide-react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
    <header className="sticky top-0 z-50 w-full border-b border-border/50 backdrop-blur-md bg-[#1E1F20]/95 shadow-lg" style={{ backgroundColor: '#1E1F20' }}>
      <div className="flex h-16 items-center gap-4 px-4 text-white">
        <SidebarTrigger className="hover:bg-white/10 transition-colors duration-200 rounded-md" />
        <div className="flex flex-1 items-center gap-4">
          <div className="flex-1 max-w-md">
            <div className="relative group/search">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/70 group-hover/search:text-white transition-colors duration-200" />
              <Input
                type="search"
                placeholder="Search..."
                className="pl-9 w-full bg-white/10 border-white/20 text-white placeholder:text-white/50 focus:bg-white/20 focus:border-primary/50 transition-all duration-200 hover:bg-white/15"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              asChild
              className="text-white hover:bg-white/10 hover:text-white transition-all duration-200 hover:scale-105"
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
              <Button variant="ghost" size="sm" className="text-white hover:bg-white/10 hover:text-white transition-all duration-200 hover:scale-110">
                <User className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

