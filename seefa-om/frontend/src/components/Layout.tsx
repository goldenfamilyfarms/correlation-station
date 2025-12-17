import { Outlet } from 'react-router-dom'
import { AppSidebar } from '@/components/app-sidebar'
import { SiteHeader } from '@/components/site-header'

export default function Layout() {
  return (
    <div className="flex flex-col h-screen">
      <SiteHeader />
      <div className="flex flex-1 overflow-hidden">
        <AppSidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="flex flex-1 flex-col gap-4 p-4 md:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}