import { Outlet } from 'react-router-dom'
import { SiteHeader } from '@/components/site-header'
import { AppSidebar } from '@/components/app-sidebar'

export default function DocsLayout() {
  return (
    <div className="flex flex-col h-screen">
      <SiteHeader />
      <div className="flex flex-1 overflow-hidden">
        <AppSidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8 lg:py-12">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
