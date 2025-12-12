import { useEffect, useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface TocItem {
  id: string
  title: string
  level: number
}

interface TableOfContentsProps {
  contentSelector?: string
  className?: string
}

export function TableOfContents({ contentSelector = 'main', className }: TableOfContentsProps) {
  const [headings, setHeadings] = useState<TocItem[]>([])
  const [activeId, setActiveId] = useState<string>('')

  useEffect(() => {
    const content = document.querySelector(contentSelector)
    if (!content) return

    const headingElements = content.querySelectorAll('h1, h2, h3, h4')
    const tocItems: TocItem[] = []

    headingElements.forEach((heading) => {
      const id = heading.id || heading.textContent?.toLowerCase().replace(/\s+/g, '-') || ''
      if (id) {
        heading.id = id
        tocItems.push({
          id,
          title: heading.textContent || '',
          level: parseInt(heading.tagName.charAt(1)),
        })
      }
    })

    setHeadings(tocItems)

    // Intersection Observer for active heading
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
          }
        })
      },
      { rootMargin: '-20% 0% -70% 0%' }
    )

    headingElements.forEach((heading) => observer.observe(heading))

    return () => {
      headingElements.forEach((heading) => observer.unobserve(heading))
    }
  }, [contentSelector])

  if (headings.length === 0) return null

  return (
    <div className={cn('w-64 border-l border-gray-200 bg-white pl-6 pr-4 py-4', className)}>
      <div className="sticky top-20 space-y-6">
        {/* Feedback Section */}
        <div>
          <h3 className="text-sm font-semibold mb-3 text-gray-900">Is this page helpful?</h3>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" className="h-8 px-3">
              <ThumbsUp className="h-4 w-4 mr-1" />
              Yes
            </Button>
            <Button variant="ghost" size="sm" className="h-8 px-3">
              <ThumbsDown className="h-4 w-4 mr-1" />
              No
            </Button>
          </div>
        </div>

        {/* Table of Contents */}
        <div>
          <h3 className="text-sm font-semibold mb-4 text-gray-900">On this page</h3>
          <nav className="space-y-1">
            {headings.map((heading) => (
              <a
                key={heading.id}
                href={`#${heading.id}`}
                className={cn(
                  'block text-sm transition-colors hover:text-foreground',
                  heading.level === 1 && 'font-semibold',
                  heading.level === 2 && 'pl-4',
                  heading.level === 3 && 'pl-8',
                  heading.level === 4 && 'pl-12',
                  activeId === heading.id
                    ? 'text-primary border-l-2 border-primary pl-2 font-medium'
                    : 'text-gray-600 hover:text-gray-900'
                )}
              >
                {heading.title}
              </a>
            ))}
          </nav>
        </div>
      </div>
    </div>
  )
}

