import { ExternalLink, LucideIcon, ArrowRight } from 'lucide-react'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useNavigate } from 'react-router-dom'

interface QuickLinkCardProps {
  title: string
  description: string
  icon: LucideIcon
  href: string
  external?: boolean
  onClick?: () => void
}

export function QuickLinkCard({
  title,
  description,
  icon: Icon,
  href,
  external = false,
  onClick,
}: QuickLinkCardProps) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (onClick) {
      onClick()
    } else if (external) {
      window.open(href, '_blank', 'noopener,noreferrer')
    } else {
      navigate(href)
    }
  }

  return (
    <Card
      className="hover:shadow-xl transition-all duration-300 cursor-pointer border-2 hover:border-primary hover:scale-105 group relative overflow-hidden"
      onClick={handleClick}
    >
      {/* Gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      <CardHeader className="relative z-10">
        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#FFF3E0] to-[#FFE0B2] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300 shadow-sm">
          <Icon className="h-7 w-7 text-[#FF9800]" />
        </div>
        <CardTitle className="flex items-center gap-2 text-lg group-hover:text-primary transition-colors">
          {title}
          {external ? (
            <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
          ) : (
            <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
          )}
        </CardTitle>
        <CardDescription className="line-clamp-2 leading-relaxed text-sm">
          {description}
        </CardDescription>
      </CardHeader>
    </Card>
  )
}

