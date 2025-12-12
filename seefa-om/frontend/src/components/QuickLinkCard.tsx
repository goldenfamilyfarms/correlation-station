import { ExternalLink, LucideIcon } from 'lucide-react'
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
      className="hover:shadow-lg transition-all cursor-pointer border-2 hover:border-primary group"
      onClick={handleClick}
    >
      <CardHeader>
        <div className="w-12 h-12 rounded-lg bg-[#FFF3E0] flex items-center justify-center mb-3 group-hover:bg-[#FFF3E0]/80 transition-colors">
          <Icon className="h-6 w-6 text-[#FF9800]" />
        </div>
        <CardTitle className="flex items-center gap-2">
          {title}
          {external && <ExternalLink className="h-4 w-4 text-muted-foreground" />}
        </CardTitle>
        <CardDescription className="line-clamp-2">{description}</CardDescription>
      </CardHeader>
    </Card>
  )
}

