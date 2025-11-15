import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { AlertCircle, Calendar, TrendingDown, TrendingUp, Edit, Save, X } from 'lucide-react'
import { format } from 'date-fns'

interface ErrorReview {
  id: number
  period: string
  created_at: string
  updated_at: string
  summary: string
  errors: ErrorDetail[]
}

interface ErrorDetail {
  id: string
  service: string
  error_type: string
  count: number
  severity: 'critical' | 'high' | 'medium' | 'low'
  description: string
  root_cause: string
  resolution_status: 'resolved' | 'in_progress' | 'planned' | 'investigating'
  action_items: string[]
  responsible_team: string
}

export default function SecaReviewsPage() {
  const [reviews, setReviews] = useState<ErrorReview[]>([])
  const [selectedReview, setSelectedReview] = useState<ErrorReview | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [editedContent, setEditedContent] = useState('')

  useEffect(() => {
    fetchReviews()
  }, [])

  const fetchReviews = async () => {
    try {
      const response = await fetch('/api/seca-reviews')
      if (response.ok) {
        const data = await response.json()
        setReviews(data)
        if (data.length > 0 && !selectedReview) {
          setSelectedReview(data[0])
        }
      }
    } catch (error) {
      console.error('Failed to fetch reviews:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveEdit = async () => {
    if (!selectedReview) return

    try {
      const response = await fetch(`/api/seca-reviews/${selectedReview.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          summary: editedContent,
        }),
      })

      if (response.ok) {
        await fetchReviews()
        setIsEditing(false)
      }
    } catch (error) {
      console.error('Failed to save review:', error)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved':
        return 'bg-green-100 text-green-800'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800'
      case 'planned':
        return 'bg-purple-100 text-purple-800'
      case 'investigating':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading SECA reviews...</div>
      </div>
    )
  }

  if (reviews.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">SECA Error Reviews</h1>
          <p className="text-lg text-gray-600">
            Bi-weekly error analysis and resolution tracking
          </p>
        </div>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No reviews available yet.</p>
              <p className="text-sm text-gray-400 mt-2">
                Reviews will be published bi-weekly with detailed error analysis.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">SECA Error Reviews</h1>
        <p className="text-lg text-gray-600">
          Bi-weekly error analysis and resolution tracking
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Reviews List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Review Periods</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {reviews.map((review) => (
                <button
                  key={review.id}
                  onClick={() => {
                    setSelectedReview(review)
                    setIsEditing(false)
                  }}
                  className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                    selectedReview?.id === review.id
                      ? 'border-grafana-orange bg-grafana-orange/5'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Calendar className="h-4 w-4 text-grafana-orange" />
                    <span className="font-semibold text-sm">{review.period}</span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {format(new Date(review.created_at), 'MMM d, yyyy')}
                  </p>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Review Detail */}
        <div className="lg:col-span-3">
          {selectedReview && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-2xl">{selectedReview.period}</CardTitle>
                    <CardDescription>
                      Last updated: {format(new Date(selectedReview.updated_at), 'MMM d, yyyy h:mm a')}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {!isEditing ? (
                      <Button
                        onClick={() => {
                          setIsEditing(true)
                          setEditedContent(selectedReview.summary)
                        }}
                        variant="outline"
                        size="sm"
                      >
                        <Edit className="h-4 w-4 mr-2" />
                        Edit
                      </Button>
                    ) : (
                      <>
                        <Button onClick={handleSaveEdit} size="sm">
                          <Save className="h-4 w-4 mr-2" />
                          Save
                        </Button>
                        <Button
                          onClick={() => setIsEditing(false)}
                          variant="outline"
                          size="sm"
                        >
                          <X className="h-4 w-4 mr-2" />
                          Cancel
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Summary */}
                <div>
                  <h3 className="font-semibold text-lg mb-3">Executive Summary</h3>
                  {isEditing ? (
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="w-full h-64 p-4 border-2 border-gray-200 rounded-lg font-mono text-sm"
                      placeholder="Enter markdown content here..."
                    />
                  ) : (
                    <div className="prose max-w-none">
                      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                        {selectedReview.summary.split('\n').map((line, idx) => (
                          <p key={idx} className="mb-2">
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <Separator />

                {/* Error Details */}
                <div>
                  <h3 className="font-semibold text-lg mb-3">Error Breakdown</h3>
                  <div className="space-y-4">
                    {selectedReview.errors.map((error) => (
                      <Card key={error.id} className="border-2">
                        <CardHeader className="pb-3">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <span className={`px-2 py-1 rounded-md text-xs font-semibold border ${getSeverityColor(error.severity)}`}>
                                  {error.severity.toUpperCase()}
                                </span>
                                <span className={`px-2 py-1 rounded-md text-xs font-semibold ${getStatusColor(error.resolution_status)}`}>
                                  {error.resolution_status.replace('_', ' ').toUpperCase()}
                                </span>
                              </div>
                              <CardTitle className="text-lg">{error.error_type}</CardTitle>
                              <CardDescription className="flex items-center gap-4 mt-1">
                                <span>Service: {error.service}</span>
                                <span>•</span>
                                <span>Occurrences: {error.count.toLocaleString()}</span>
                              </CardDescription>
                            </div>
                            <div className="flex items-center gap-2">
                              {error.count > 1000 ? (
                                <TrendingUp className="h-5 w-5 text-red-500" />
                              ) : (
                                <TrendingDown className="h-5 w-5 text-green-500" />
                              )}
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Description</h4>
                            <p className="text-sm text-gray-600">{error.description}</p>
                          </div>

                          <div>
                            <h4 className="font-semibold text-sm mb-1">Root Cause</h4>
                            <p className="text-sm text-gray-600">{error.root_cause}</p>
                          </div>

                          <div>
                            <h4 className="font-semibold text-sm mb-1">Action Items</h4>
                            <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                              {error.action_items.map((item, idx) => (
                                <li key={idx}>{item}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="flex items-center gap-2 text-sm">
                            <span className="font-semibold">Responsible Team:</span>
                            <span className="px-2 py-1 bg-grafana-orange/10 text-grafana-orange rounded">
                              {error.responsible_team}
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
