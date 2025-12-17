import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'

interface KpiCardProps {
  title: string
  value: string | number
  description?: string
  icon?: LucideIcon
  trend?: {
    value: string | number
    label: string
    positive?: boolean
  }
}

export function KpiCard({ title, value, description, icon: Icon, trend }: KpiCardProps) {
  return (
    <Card className="hover:shadow-xl transition-all duration-500 border-l-4 border-l-primary/30 hover:border-l-primary group relative overflow-hidden bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
      {/* Animated background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Left border glow effect */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary/0 via-primary/50 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 relative z-10">
        <CardTitle className="text-sm font-semibold text-muted-foreground group-hover:text-foreground transition-colors duration-300">
          {title}
        </CardTitle>
        {Icon && (
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary/10 via-primary/5 to-accent/10 flex items-center justify-center group-hover:scale-110 group-hover:rotate-3 transition-all duration-500 shadow-md group-hover:shadow-lg group-hover:shadow-primary/20 relative overflow-hidden">
            {/* Icon glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 opacity-0 group-hover:opacity-100 blur-md transition-opacity duration-500" />
            <Icon className="h-6 w-6 text-primary relative z-10 group-hover:text-accent transition-colors duration-300" />
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-3 relative z-10">
        <div className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text text-transparent group-hover:from-primary group-hover:to-accent transition-all duration-500">
          {value}
        </div>
        {description && (
          <CardDescription className="text-sm leading-relaxed text-muted-foreground group-hover:text-foreground/70 transition-colors duration-300">
            {description}
          </CardDescription>
        )}
        {trend && (
          <Badge
            variant={trend.positive ? "default" : "destructive"}
            className="flex items-center gap-1.5 w-fit px-2.5 py-1 group-hover:scale-105 transition-transform duration-300 shadow-sm"
          >
            {trend.positive ? (
              <TrendingUp className="h-3.5 w-3.5" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5" />
            )}
            <span className="text-xs font-semibold">
              {trend.value} {trend.label}
            </span>
          </Badge>
        )}
      </CardContent>
    </Card>
  )
}

