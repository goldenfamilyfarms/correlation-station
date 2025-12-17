import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { SiteHeader } from '@/components/site-header'
import { DocsSidebar } from '@/components/DocsSidebar'
import { Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DocsLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <SiteHeader />

      <div className="flex flex-1 relative">
        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar - Mobile Drawer / Desktop Fixed */}
        <aside
          className={`
            fixed lg:sticky top-16 left-0 z-50 lg:z-0
            w-72 h-[calc(100vh-4rem)]
            transform transition-transform duration-300 ease-in-out
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            border-r border-border overflow-y-auto
          `}
        >
          {/* Close button for mobile */}
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
          <DocsSidebar />
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          {/* Mobile Menu Button */}
          <Button
            variant="outline"
            size="sm"
            className="fixed bottom-4 left-4 z-30 lg:hidden bg-primary text-white hover:bg-primary/90 shadow-lg"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5 mr-2" />
            Menu
          </Button>

          <div className="max-w-5xl mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8 lg:py-12">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
