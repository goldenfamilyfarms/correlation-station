import { AlertCircle, RefreshCw, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ErrorResponse } from '@/lib/httpClient'

interface ErrorBannerProps {
  error: ErrorResponse
  onRetry?: () => void
  onDismiss?: () => void
}

export default function ErrorBanner({ error, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded">
      <div className="flex items-start">
        <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 mr-3" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-800">
            {error.service} Error ({error.status})
          </h3>
          <p className="text-sm text-red-700 mt-1">{error.message}</p>
          <div className="mt-2 text-xs text-red-600 space-y-1">
            <div><span className="font-semibold">Route:</span> {error.route}</div>
            {error.correlationId && (
              <div><span className="font-semibold">Correlation ID:</span> {error.correlationId}</div>
            )}
          </div>
          <div className="mt-3 flex gap-2">
            {onRetry && (
              <Button size="sm" variant="outline" onClick={onRetry} className="h-8">
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.open('/documentation', '_blank')}
              className="h-8"
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              Diagnostics
            </Button>
            {onDismiss && (
              <Button size="sm" variant="ghost" onClick={onDismiss} className="h-8">
                Dismiss
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
