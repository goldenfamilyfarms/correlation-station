import { useState } from 'react'
import { 
  BookOpen, 
  Network, 
  Code, 
  HelpCircle,
  ChevronRight,
  Search
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'

// Define sections here to avoid circular dependency
const docsSections = [
  {
    id: 'overview',
    title: 'Overview',
    icon: BookOpen,
    subsections: [
      { id: 'what-is', title: 'What is Correlation Station' },
      { id: 'problems', title: 'Problems we were solving' },
      { id: 'architecture-diagram', title: 'High-level architecture' },
    ],
  },
  {
    id: 'architecture',
    title: 'Architecture & Design Decisions',
    icon: Network,
    subsections: [
      { id: 'why-grafana', title: 'Why Grafana' },
      { id: 'why-alloy', title: 'Why Grafana Alloy agent on MDSO' },
      { id: 'constraints', title: 'Constraints of Solution Manager' },
      { id: 'correlation-engine', title: 'Why a Correlation Engine' },
      { id: 'redis-caching', title: 'Redis caching & backpressure' },
      { id: 'horizontal-scaling', title: 'Horizontal scaling' },
    ],
  },
  {
    id: 'query-reference',
    title: 'Query Reference',
    icon: Code,
    subsections: [
      { id: 'logql', title: 'LogQL examples' },
      { id: 'traceql', title: 'TraceQL examples' },
      { id: 'promql', title: 'PromQL examples' },
    ],
  },
  {
    id: 'faq',
    title: 'FAQ & Glossary',
    icon: HelpCircle,
    subsections: [],
  },
]

interface DocsSidebarProps {
  currentSection?: string
  currentSubsection?: string
}

export function DocsSidebar({ currentSection, currentSubsection }: DocsSidebarProps) {
  const [expandedSections, setExpandedSections] = useState<string[]>(['overview'])

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) =>
      prev.includes(sectionId)
        ? prev.filter((id) => id !== sectionId)
        : [...prev, sectionId]
    )
  }

  return (
    <div className="w-64 border-r bg-[#1a1a1a] text-white h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-700">
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="search"
            placeholder="Search docs (⌘K)"
            className="pl-9 bg-gray-800 border-gray-700 text-white placeholder:text-gray-400 h-8 text-sm"
            readOnly
          />
        </div>
        <h2 className="font-semibold text-lg text-white">Documentation</h2>
        <p className="text-sm text-gray-400 mt-1">Observability Handbook</p>
      </div>
      <nav className="p-2">
        {docsSections.map((section) => {
          const Icon = section.icon
          const isExpanded = expandedSections.includes(section.id)
          const isActive = currentSection === section.id

          return (
            <div key={section.id} className="mb-1">
              <button
                onClick={() => toggleSection(section.id)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-white border-l-2 border-primary"
                    : "hover:bg-gray-800 text-gray-300"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="flex-1 text-left">{section.title}</span>
                {section.subsections.length > 0 && (
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 transition-transform",
                      isExpanded && "rotate-90"
                    )}
                  />
                )}
              </button>
              {isExpanded && section.subsections.length > 0 && (
                <div className="ml-6 mt-1 space-y-1">
                  {section.subsections.map((subsection) => {
                    const isSubActive = currentSubsection === subsection.id
                    return (
                      <a
                        key={subsection.id}
                        href={`#${subsection.id}`}
                        className={cn(
                          "block px-3 py-1.5 rounded-md text-sm transition-colors",
                          isSubActive
                            ? "bg-primary/20 text-primary font-medium border-l-2 border-primary"
                            : "text-gray-400 hover:text-white hover:bg-gray-800"
                        )}
                      >
                        {subsection.title}
                      </a>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </nav>
    </div>
  )
}
