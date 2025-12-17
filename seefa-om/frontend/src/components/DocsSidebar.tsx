import { useState } from 'react'
import {
  BookOpen,
  Network,
  Code,
  Lightbulb,
  FileText,
  Home
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Link } from 'react-router-dom'

const docsSections = [
  {
    id: 'overview',
    title: 'Overview',
    icon: BookOpen,
    description: 'Introduction and architecture',
  },
  {
    id: 'architecture',
    title: 'Architecture',
    icon: Lightbulb,
    description: 'Design decisions',
  },
  {
    id: 'query-reference',
    title: 'Query Reference',
    icon: Code,
    description: 'LogQL, TraceQL, PromQL',
  },
]

const quickLinks = [
  { title: 'Home', href: '/', icon: Home },
  { title: 'Tutorials', href: '/netdev101', icon: FileText },
  { title: 'SECA Reviews', href: '/seca-review', icon: Network },
]

export function DocsSidebar() {
  const [activeSection] = useState('overview')

  return (
    <div className="w-full bg-[#1a1a1a] text-white h-full overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-gray-700">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center">
            <BookOpen className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="font-bold text-lg text-white">Documentation</h2>
            <p className="text-xs text-gray-400">Observability Handbook</p>
          </div>
        </div>
      </div>

      {/* Main Sections */}
      <div className="p-4">
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-3">
            Sections
          </h3>
          <nav className="space-y-1">
            {docsSections.map((section) => {
              const Icon = section.icon
              const isActive = activeSection === section.id

              return (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  className={cn(
                    "flex items-start gap-3 px-3 py-3 rounded-lg transition-all group",
                    isActive
                      ? "bg-primary/10 border-l-2 border-primary"
                      : "hover:bg-gray-800 border-l-2 border-transparent"
                  )}
                >
                  <Icon className={cn(
                    "h-5 w-5 mt-0.5 flex-shrink-0",
                    isActive ? "text-primary" : "text-gray-400 group-hover:text-white"
                  )} />
                  <div className="flex-1 min-w-0">
                    <div className={cn(
                      "font-medium text-sm",
                      isActive ? "text-white" : "text-gray-300 group-hover:text-white"
                    )}>
                      {section.title}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {section.description}
                    </div>
                  </div>
                </a>
              )
            })}
          </nav>
        </div>

        {/* Quick Links */}
        <div className="pt-4 border-t border-gray-700">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-3">
            Quick Links
          </h3>
          <nav className="space-y-1">
            {quickLinks.map((link) => {
              const Icon = link.icon
              return (
                <Link
                  key={link.href}
                  to={link.href}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-all group"
                >
                  <Icon className="h-4 w-4" />
                  <span>{link.title}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </div>
    </div>
  )
}
