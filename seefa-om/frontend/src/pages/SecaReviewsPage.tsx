import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { 
  TrendingDown, 
  TrendingUp, 
  Upload, 
  ExternalLink,
  Download
} from 'lucide-react'
import { SecaUploadModal } from '@/components/SecaUploadModal'
import { format } from 'date-fns'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'

interface SecaError {
  id: string
  circuit_id: string
  date: string
  service_request_type: string
  product_name: string
  error_message: string
  cdnc_summary: string
  fallout_reason: string
  priority: 'high' | 'medium' | 'low' | 'critical'
  application: string
  team: string
  owner: string
  status: 'new' | 'triage' | 'resolved' | 'in_progress'
  grafana_link?: string
  meta_web_link?: string
  analysis_pdf_url?: string
}

interface SecaWeek {
  id: string
  week_start_date: string
  week_end_date: string
  summary_text: string
  total_circuits: number
  circuits_with_traceback: number
  errors: SecaError[]
}

// Mock data - TODO: Replace with API calls
const mockWeeks: SecaWeek[] = [
  {
    id: 'week-1',
    week_start_date: '2025-12-02',
    week_end_date: '2025-12-08',
    summary_text: 'This week saw 42 SECA errors, primarily in ARDA and BEORN services. Most issues were related to timeout errors and configuration mismatches.',
    total_circuits: 42,
    circuits_with_traceback: 38,
    errors: [
      {
        id: '1',
        circuit_id: '33.L1XX.801233..TWCC',
        date: '2025-12-05',
        service_request_type: 'Provision',
        product_name: 'ELINE',
        error_message: 'Timeout during compliance check',
        cdnc_summary: 'Circuit provisioning failed',
        fallout_reason: 'Compliance timeout',
        priority: 'high',
        application: 'ARDA',
        team: 'Compliance Team',
        owner: 'John D.',
        status: 'triage',
        grafana_link: 'http://159.56.4.94:3000',
        meta_web_link: 'http://159.56.4.94/reports',
      },
      {
        id: '2',
        circuit_id: '61.TGXX.000860..CHTR',
        date: '2025-12-06',
        service_request_type: 'Modify',
        product_name: 'ELAN',
        error_message: 'KeyError: layer2-policer',
        cdnc_summary: 'Configuration error',
        fallout_reason: 'Parse error',
        priority: 'critical',
        application: 'BEORN',
        team: 'Compliance Team',
        owner: 'Jane S.',
        status: 'in_progress',
      },
    ],
  },
]

const trendData = [
  { week: 'Week 1', errors: 38, high: 12, medium: 20, low: 6 },
  { week: 'Week 2', errors: 42, high: 15, medium: 22, low: 5 },
  { week: 'Week 3', errors: 35, high: 10, medium: 20, low: 5 },
  { week: 'Week 4', errors: 40, high: 14, medium: 21, low: 5 },
]

export default function SecaReviewsPage() {
  const [selectedWeek, setSelectedWeek] = useState<string>('this-week')
  const [currentWeek, setCurrentWeek] = useState<SecaWeek | null>(mockWeeks[0])
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [filterPriority, setFilterPriority] = useState<string>('all')
  const [filterApp, setFilterApp] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    // TODO: Fetch week data based on selection
    if (selectedWeek === 'this-week') {
      setCurrentWeek(mockWeeks[0])
    } else if (selectedWeek === 'last-week') {
      // Mock last week data
      setCurrentWeek({
        ...mockWeeks[0],
        id: 'week-0',
        week_start_date: '2025-11-25',
        week_end_date: '2025-12-01',
        total_circuits: 38,
      })
    }
  }, [selectedWeek])

  const filteredErrors = currentWeek?.errors.filter((error) => {
    if (filterPriority !== 'all' && error.priority !== filterPriority) return false
    if (filterApp !== 'all' && error.application !== filterApp) return false
    if (searchQuery && !error.circuit_id.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !error.error_message.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  }) || []

  const breakdownByPriority = currentWeek?.errors.reduce((acc, error) => {
    acc[error.priority] = (acc[error.priority] || 0) + 1
    return acc
  }, {} as Record<string, number>) || {}


  return (
    <div className="flex flex-1 flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">SECA Review</h1>
          <p className="text-muted-foreground">
            Weekly automation error analysis and resolution tracking
          </p>
        </div>
        <Button onClick={() => setUploadModalOpen(true)}>
          <Upload className="h-4 w-4 mr-2" />
          Upload SECA XLSX
        </Button>
      </div>

      {/* Week Selector */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Select value={selectedWeek} onValueChange={setSelectedWeek}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select week" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="this-week">This Week</SelectItem>
                <SelectItem value="last-week">Last Week</SelectItem>
                <SelectItem value="custom">Custom Range</SelectItem>
              </SelectContent>
            </Select>
            {currentWeek && (
              <div className="text-sm text-muted-foreground">
                {format(new Date(currentWeek.week_start_date), 'MMM d')} - {format(new Date(currentWeek.week_end_date), 'MMM d, yyyy')}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Top Summary Card */}
      {currentWeek && (
        <Card>
          <CardHeader>
            <CardTitle>Week Summary</CardTitle>
            <CardDescription>Overview of this week's SECA errors</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <div className="text-3xl font-bold">{currentWeek.total_circuits}</div>
                <div className="text-sm text-muted-foreground">Total SECA Errors</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {currentWeek.total_circuits - (mockWeeks[0]?.total_circuits || 0) > 0 ? (
                    <span className="text-red-500 flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      +{currentWeek.total_circuits - (mockWeeks[0]?.total_circuits || 0)} vs last week
                    </span>
                  ) : (
                    <span className="text-green-500 flex items-center gap-1">
                      <TrendingDown className="h-3 w-3" />
                      {Math.abs(currentWeek.total_circuits - (mockWeeks[0]?.total_circuits || 0))} vs last week
                    </span>
                  )}
                </div>
              </div>
              <div>
                <div className="text-3xl font-bold">{currentWeek.circuits_with_traceback}</div>
                <div className="text-sm text-muted-foreground">With Tracebacks</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {Math.round((currentWeek.circuits_with_traceback / currentWeek.total_circuits) * 100)}% coverage
                </div>
              </div>
              <div>
                <div className="text-3xl font-bold">
                  {currentWeek.errors.filter((e) => e.status === 'resolved').length}
                </div>
                <div className="text-sm text-muted-foreground">Resolved</div>
              </div>
              <div>
                <div className="text-3xl font-bold">
                  {currentWeek.errors.filter((e) => e.status === 'new' || e.status === 'triage').length}
                </div>
                <div className="text-sm text-muted-foreground">Open</div>
              </div>
            </div>
            {currentWeek.summary_text && (
              <div className="mt-4 p-3 bg-muted rounded-lg">
                <p className="text-sm">{currentWeek.summary_text}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Error Count Over Time</CardTitle>
            <CardDescription>Weekly error trends</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="errors" stroke="#316CB8" name="Total Errors" />
                <Line type="monotone" dataKey="high" stroke="#F44336" name="High Priority" />
                <Line type="monotone" dataKey="medium" stroke="#FDD835" name="Medium Priority" />
                <Line type="monotone" dataKey="low" stroke="#388E3C" name="Low Priority" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Breakdown by Priority</CardTitle>
            <CardDescription>Error distribution</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={[
                { name: 'High', value: breakdownByPriority.high || 0 },
                { name: 'Medium', value: breakdownByPriority.medium || 0 },
                { name: 'Low', value: breakdownByPriority.low || 0 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#316CB8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Error Log */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Error Log</CardTitle>
              <CardDescription>Detailed error records for this week</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Input
                placeholder="Search circuits or errors..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64"
              />
              <Select value={filterPriority} onValueChange={setFilterPriority}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterApp} onValueChange={setFilterApp}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="App" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="ARDA">ARDA</SelectItem>
                  <SelectItem value="BEORN">BEORN</SelectItem>
                  <SelectItem value="PALANTIR">PALANTIR</SelectItem>
                  <SelectItem value="MDSO">MDSO</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            <div className="grid grid-cols-8 gap-4 pb-2 border-b text-sm font-medium text-muted-foreground">
              <div>Circuit ID</div>
              <div>Fallout Reason</div>
              <div>Priority</div>
              <div>Application</div>
              <div>Team</div>
              <div>Owner</div>
              <div>Status</div>
              <div>Links</div>
            </div>
            {filteredErrors.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">
                No errors found matching filters
              </div>
            ) : (
              filteredErrors.map((error) => (
                <div key={error.id} className="grid grid-cols-8 gap-4 py-3 border-b last:border-0 text-sm">
                  <div className="font-medium">{error.circuit_id}</div>
                  <div>{error.fallout_reason}</div>
                  <div>
                    <Badge
                      variant={
                        error.priority === 'high' || error.priority === 'critical'
                          ? 'destructive'
                          : error.priority === 'medium'
                          ? 'secondary'
                          : 'outline'
                      }
                      className={
                        error.priority === 'critical' ? 'bg-red-600' : ''
                      }
                    >
                      {error.priority}
                    </Badge>
                  </div>
                  <div>{error.application}</div>
                  <div>{error.team}</div>
                  <div>{error.owner}</div>
                  <div>
                    <Badge
                      variant={
                        error.status === 'resolved'
                          ? 'default'
                          : error.status === 'triage'
                          ? 'secondary'
                          : 'outline'
                      }
                    >
                      {error.status}
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    {error.grafana_link && (
                      <Button variant="ghost" size="sm" className="h-7" asChild>
                        <a href={error.grafana_link} target="_blank" rel="noopener noreferrer">
                          Grafana <ExternalLink className="h-3 w-3 ml-1" />
                        </a>
                      </Button>
                    )}
                    {error.meta_web_link && (
                      <Button variant="ghost" size="sm" className="h-7" asChild>
                        <a href={error.meta_web_link} target="_blank" rel="noopener noreferrer">
                          Meta <ExternalLink className="h-3 w-3 ml-1" />
                        </a>
                      </Button>
                    )}
                    {error.analysis_pdf_url && (
                      <Button variant="ghost" size="sm" className="h-7" asChild>
                        <a href={error.analysis_pdf_url} download>
                          PDF <Download className="h-3 w-3 ml-1" />
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Upload Modal */}
      <SecaUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onSuccess={() => {
          // Refresh week data after successful upload
          // TODO: Refetch current week data
          setUploadModalOpen(false)
        }}
      />
    </div>
  )
}
