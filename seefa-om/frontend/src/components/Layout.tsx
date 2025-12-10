import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { Activity, Home, BookOpen, Network, AlertCircle, GraduationCap, LogIn, LogOut, User, Upload } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import LoginModal from './LoginModal'
import { Button } from './ui/button'

export default function Layout() {
  const location = useLocation()
  const { user, isAuthenticated, logout } = useAuth()
  const [loginOpen, setLoginOpen] = useState(false)

  const navigation = [
    { name: 'Home', href: '/', icon: Home },
    { name: 'Documentation', href: '/docs', icon: BookOpen },
    { name: 'Architecture', href: '/architecture', icon: Network },
    { name: 'SECA Reviews', href: '/seca-reviews', icon: AlertCircle },
    { name: 'SECA Upload', href: '/seca-upload', icon: Upload },
    { name: 'Tutorials', href: '/tutorials', icon: GraduationCap },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center gap-3">
              <Activity className="h-8 w-8 text-grafana-orange" />
              <h1 className="text-2xl font-bold text-gray-900">
                Correlation Station
              </h1>
            </div>
            <div className="flex items-center gap-6">
              <nav className="flex gap-6">
                {navigation.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-grafana-orange text-white'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  )
                })}
              </nav>
              
              {isAuthenticated ? (
                <div className="flex items-center gap-3 border-l pl-6">
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-gray-500" />
                    <span className="text-gray-700">{user?.username}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={logout}
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  onClick={() => setLoginOpen(true)}
                  className="bg-grafana-orange hover:bg-grafana-orange/90"
                >
                  <LogIn className="h-4 w-4 mr-1" />
                  Login
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Correlation Station - Observability & Monitoring Training Platform
          </p>
        </div>
      </footer>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  )
}