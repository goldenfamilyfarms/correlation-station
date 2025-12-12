import { Badge } from '@/components/ui/badge'

interface HealthRowProps {
  service: string
  status: 'healthy' | 'partial' | 'limited'
  description?: string
}

const statusConfig = {
  healthy: { label: 'Healthy', variant: 'default' as const, className: 'bg-green-500' },
  partial: { label: 'Partial', variant: 'secondary' as const, className: 'bg-yellow-500' },
  limited: { label: 'Limited', variant: 'destructive' as const, className: 'bg-red-500' },
}

export function HealthRow({ service, status, description }: HealthRowProps) {
  const config = statusConfig[status]

  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <div className="flex-1">
        <div className="font-medium">{service}</div>
        {description && <div className="text-sm text-muted-foreground">{description}</div>}
      </div>
      <Badge variant={config.variant} className={config.className}>
        {config.label}
      </Badge>
    </div>
  )
}

