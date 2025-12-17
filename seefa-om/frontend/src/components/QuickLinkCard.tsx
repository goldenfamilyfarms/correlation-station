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
      className="hover:shadow-2xl transition-all duration-500 cursor-pointer border border-border/50 hover:border-primary/50 hover:scale-[1.02] group relative overflow-hidden bg-gradient-to-br from-card to-card/95 backdrop-blur-sm"
      onClick={handleClick}
    >
      {/* Animated gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Shine effect on hover */}
      <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      
      {/* Subtle border glow */}
      <div className="absolute inset-0 rounded-lg border-2 border-primary/0 group-hover:border-primary/20 transition-colors duration-300 pointer-events-none" />

      <CardHeader className="relative z-10">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/20 via-accent/10 to-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 group-hover:rotate-3 transition-all duration-500 shadow-lg group-hover:shadow-xl group-hover:shadow-primary/20 relative overflow-hidden">
          {/* Icon background glow */}
          <div className="absolute inset-0 bg-gradient-to-br from-accent/30 to-primary/20 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500" />
          <Icon className="h-8 w-8 text-accent relative z-10 group-hover:text-primary transition-colors duration-300" />
        </div>
        <CardTitle className="flex items-center gap-2 text-lg font-bold group-hover:text-primary transition-colors duration-300 mb-1">
          {title}
          <span className="ml-auto">
            {external ? (
              <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:scale-110 transition-all duration-300" />
            ) : (
              <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all duration-300" />
            )}
          </span>
        </CardTitle>
        <CardDescription className="line-clamp-2 leading-relaxed text-sm text-muted-foreground group-hover:text-foreground/80 transition-colors duration-300">
          {description}
        </CardDescription>
      </CardHeader>
    </Card>
  )
}

