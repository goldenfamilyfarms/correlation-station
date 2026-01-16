# Correlation Engine Front-End Architecture

## Overview

The Correlation Station front-end is a modern React 18.3 Single Page Application (SPA) built with TypeScript, featuring real-time telemetry visualization, SECA error tracking, and comprehensive observability dashboards. The application is located at `/seefa-om/frontend/` and serves as the user interface for the SEEFA Observability Monitoring system.

---

## 1. Optimization Strategies

### Build & Development Optimization

#### **Vite Build Tool (v5.4.10)**
- **Fast Hot Module Replacement (HMR)**: Sub-second refresh times during development
- **ES Module-based**: Native browser ESM support for faster dev server startup
- **Optimized Production Builds**: Automatic code splitting and tree-shaking
- **Asset Optimization**: Built-in image and CSS optimization

**Configuration** (`vite.config.ts`):
```typescript
{
  base: '/correlation-station/',
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8080'  // Backend proxy
    }
  }
}
```

#### **TypeScript Strict Mode**
- Type safety eliminates runtime errors
- Unused variable detection (`noUnusedLocals`, `noUnusedParameters`)
- Enhanced IDE autocomplete and refactoring support

### Runtime Optimization

#### **Code Splitting via React Router**
- Route-based lazy loading with `React.lazy()` (ready for implementation)
- Separate bundles for each major page reduces initial load time
- Dynamic imports for heavy components

#### **State Persistence**
- **Zustand with localStorage middleware**: Reduces redundant API calls
- Authentication state persists across sessions
- Tutorial progress cached locally
- Automatic hydration on app load

#### **Responsive Design**
- **Tailwind CSS**: JIT compilation generates only used styles (~10-20KB in production)
- **Responsive Recharts**: `<ResponsiveContainer>` adapts to viewport changes
- Mobile-first breakpoints (sm, md, lg, xl)

#### **Component Optimization Opportunities** (Currently Not Implemented)
```typescript
// Recommended additions:
import { memo } from 'react'
import { useMemo, useCallback } from 'react'

// Memoize expensive computations
const chartData = useMemo(() => processData(rawData), [rawData])

// Memoize callbacks to prevent re-renders
const handleClick = useCallback(() => {...}, [deps])

// Memoize components with frequent re-renders
export const KpiCard = memo(({ title, value }) => {...})
```

#### **HTTP Client Error Handling**
- Centralized error extraction and correlation ID tracking
- Service name detection from route patterns
- Automatic retry logic (can be added)
- Request deduplication opportunities

### Asset Optimization

#### **Icon System**
- **Lucide React**: Tree-shakeable icons (only imported icons are bundled)
- SVG-based for crisp rendering at any scale
- No icon font download overhead

#### **CSS Strategy**
- **Tailwind CSS Purge**: Removes unused classes in production
- **CSS Variables**: Dynamic theming without JavaScript
- **Minimal Global CSS**: Only critical styles in `index.css`

---

## 2. Component Architecture

### Architectural Pattern: **Atomic Design + Container/Presentational**

#### **Component Hierarchy**

```
┌─────────────────────────────────────────┐
│          App.tsx (Router)               │
│  ┌───────────────────────────────────┐  │
│  │      Layout.tsx (Shell)           │  │
│  │  ┌─────────────┬────────────────┐ │  │
│  │  │ AppSidebar  │  SiteHeader    │ │  │
│  │  └─────────────┴────────────────┘ │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  <Outlet /> (Page Router)   │  │  │
│  │  │  ┌───────────────────────┐  │  │  │
│  │  │  │  CorrelationEnginePage│  │  │  │
│  │  │  │   ├─ KpiCard         │  │  │  │
│  │  │  │   ├─ LineChart       │  │  │  │
│  │  │  │   └─ Card/Badge/etc  │  │  │  │
│  │  │  └───────────────────────┘  │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Component Layers

#### **1. Atoms** (`/src/components/ui/`)
Radix UI primitive wrappers with custom styling:
- `button.tsx`: Interactive button with variants
- `badge.tsx`: Status indicators (default/secondary/destructive/outline)
- `card.tsx`: Container with header/content/footer sections
- `input.tsx`: Form input with validation states
- `select.tsx`: Dropdown selection
- `dialog.tsx`: Modal overlay
- `tooltip.tsx`: Hover information
- `progress.tsx`: Progress bars
- `separator.tsx`: Visual dividers
- `tabs.tsx`: Tabbed navigation

**Design Principles**:
- Composition over inheritance
- Accessible by default (Radix UI primitives)
- Styled with Tailwind + Class Variance Authority (CVA)
- Controlled and uncontrolled variants

#### **2. Molecules** (`/src/components/`)
Composite UI components:
- **`KpiCard`**: Metric display card with icon, value, trend indicator
  - Animated hover effects (scale, rotate, gradient overlays)
  - Gradient borders and glow effects
  - Responsive to group hover states
- **`HealthRow`**: Service status badge row
- **`CodeBlock`**: Syntax-highlighted code display (React Syntax Highlighter)
- **`ErrorBanner`**: Contextual error notifications
- **`LoginModal`**: Authentication dialog
- **`SecaUploadModal`**: File upload interface
- **`QuickLinkCard`**: Navigation shortcuts

#### **3. Organisms** (`/src/components/`)
Complex, feature-complete sections:
- **`Layout`**: Application shell with header + sidebar + main content
- **`AppSidebar`**: Primary navigation with sections:
  - Grafana Stack links
  - Compliance & SECA tools
  - Overview pages
  - External tool links (Grafana, Prometheus, Pyroscope)
- **`SiteHeader`**: Top navigation bar with auth status
- **`DocsLayout`**: Documentation-specific layout with sidebar TOC
- **`TableOfContents`**: Auto-generated TOC from markdown headings

#### **4. Pages** (`/src/pages/`)
Top-level route components (containers):
- **`HomePage`**: Landing carousel with feature overview
- **`CorrelationEnginePage`**: Real-time metrics dashboard
  - KPI cards (requests, throughput, error rate, dropped items)
  - Dual-axis line chart (requests + errors over 30 min)
  - Latency metrics (avg, P95)
  - OpenTelemetry metrics (spans/min, dropped spans)
  - Recent issues table with Grafana links
- **`SecaReviewsPage`**: SECA error analysis dashboard
  - Weekly error summaries with trend indicators
  - Priority breakdown (high/medium/low/critical)
  - Filterable error log table
  - Line/bar chart visualizations
  - Export and upload functionality
- **`LoginPage`**: Authentication entry point
- **`CompliancePage`**: Compliance documentation
- **`ArchitecturePage`**: System architecture diagrams
- **`TutorialsPageNew`**: Interactive learning modules

### Component Composition Example

```tsx
// Page (Container)
<CorrelationEnginePage>
  {/* Organism */}
  <div className="grid">
    {/* Molecule */}
    <KpiCard
      title="Throughput"
      value="1250/s"
      icon={Zap}
      trend={{ value: 0.5, positive: true }}
    >
      {/* Atoms */}
      <Card>
        <CardHeader>
          <CardTitle />
        </CardHeader>
        <CardContent>
          <Badge variant="default" />
        </CardContent>
      </Card>
    </KpiCard>
  </div>
</CorrelationEnginePage>
```

### Styling Architecture

#### **Tailwind CSS + CVA (Class Variance Authority)**
```tsx
// Example: Button with variants
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        destructive: "bg-destructive text-destructive-foreground",
        outline: "border border-input bg-background",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      }
    }
  }
)
```

#### **CSS Custom Properties** (`index.css`)
```css
:root {
  --background: #F8F9FA;
  --primary: #1B6AC7;
  --accent: #FF9800;
  --destructive: #F44336;
  --muted-foreground: #A0A0A0;
}
```

#### **Advanced Animation Techniques**
- CSS transitions for state changes (hover, focus)
- Transform effects (scale, rotate, translate)
- Gradient animations on hover
- Backdrop blur effects
- Glow/shadow effects with opacity transitions

---

## 3. State Management Strategies

### Architecture: **Zustand + Local State Hybrid**

#### **Why Zustand?**
- **Minimal Boilerplate**: No providers, actions, or reducers
- **TypeScript-First**: Excellent type inference
- **Small Bundle Size**: ~1KB gzipped
- **No Context Provider Hell**: Direct store access
- **Middleware Support**: Persistence, devtools, immer

### Global State Stores

#### **1. Authentication Store** (`/src/lib/auth.ts`)

```typescript
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      login: async (username, password) => {
        const response = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          body: JSON.stringify({ username, password })
        })
        const user = await response.json()
        set({ user, isAuthenticated: true })
      },
      logout: () => set({ user: null, isAuthenticated: false })
    }),
    { name: 'auth-storage' }  // localStorage key
  )
)
```

**Usage in Components**:
```tsx
function Header() {
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <div>
      {isAuthenticated ? (
        <>
          <span>Welcome, {user?.username}</span>
          <button onClick={logout}>Logout</button>
        </>
      ) : (
        <Link to="/login">Login</Link>
      )}
    </div>
  )
}
```

**Benefits**:
- No prop drilling
- Automatic localStorage persistence
- Re-renders only components using auth state
- Type-safe access to user data

#### **2. Progress Tracking Store** (`/src/lib/progress.ts`)

```typescript
interface ProgressState {
  completedTutorials: Record<string, string[]>  // userId -> tutorialIds
  markComplete: (userId: string, tutorialId: string) => Promise<void>
  isComplete: (userId: string, tutorialId: string) => boolean
  getProgress: (userId: string, totalTutorials: number) => number
  loadProgress: (userId: string) => Promise<void>
}

export const useProgress = create<ProgressState>()(
  persist(
    (set, get) => ({
      completedTutorials: {},
      markComplete: async (userId, tutorialId) => {
        await fetch(`${API_BASE}/progress`, {
          method: 'POST',
          body: JSON.stringify({ userId, tutorialId })
        })
        set((state) => ({
          completedTutorials: {
            ...state.completedTutorials,
            [userId]: [...(state.completedTutorials[userId] || []), tutorialId]
          }
        }))
      },
      isComplete: (userId, tutorialId) => {
        return get().completedTutorials[userId]?.includes(tutorialId) || false
      }
    }),
    { name: 'progress-storage' }
  )
)
```

### Local Component State

#### **useState for UI State**
```tsx
function SecaReviewsPage() {
  // Local UI state (not shared between components)
  const [selectedWeek, setSelectedWeek] = useState<string>('this-week')
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [filterPriority, setFilterPriority] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Computed state
  const filteredErrors = currentWeek?.errors.filter((error) => {
    if (filterPriority !== 'all' && error.priority !== filterPriority) return false
    if (searchQuery && !error.circuit_id.includes(searchQuery)) return false
    return true
  })

  return <div>{/* Render filtered data */}</div>
}
```

#### **useEffect for Side Effects**
```tsx
function CorrelationEnginePage() {
  const [stats, setStats] = useState(mockStats)

  useEffect(() => {
    // Poll API every 30 seconds
    const interval = setInterval(() => {
      fetch('/correlation-engine/stats/current')
        .then(res => res.json())
        .then(data => setStats(data))
    }, 30000)

    return () => clearInterval(interval)  // Cleanup
  }, [])

  return <Dashboard stats={stats} />
}
```

### State Management Decision Matrix

| State Type | Storage Location | Example |
|------------|------------------|---------|
| Authentication | Zustand + localStorage | User session, JWT tokens |
| User Preferences | Zustand + localStorage | Theme, tutorial progress |
| API Data (Shared) | Zustand | Shared metrics, config |
| API Data (Page-specific) | Local useState | Dashboard stats, SECA errors |
| Form Input | Local useState | Search query, filters |
| Modal State | Local useState | Dialog open/close |
| Computed Values | useMemo | Filtered lists, calculations |

### HTTP Client Architecture

**Custom HttpClient** (`/src/lib/httpClient.ts`):
```typescript
class HttpClient {
  private baseURL: string

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`)
    return this.handleResponse(response, path)
  }

  private async handleResponse(response: Response, route: string) {
    if (!response.ok) {
      // Extract service name, correlation ID
      throw {
        service: this.extractServiceName(route),
        correlationId: response.headers.get('x-correlation-id'),
        status: response.status,
        message: error.message || response.statusText
      }
    }
    return response.json()
  }
}
```

**Benefits**:
- Centralized error handling
- Automatic correlation ID extraction
- Service name detection from routes
- Type-safe responses

---

## 4. Telemetry Visualization Without Grafana

### Scenario: Self-Contained React Dashboard

If we **weren't using Grafana** as the primary visualization tool and instead handled all telemetry visualization in the React front-end, here's the architecture:

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Multiple Backends                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Tempo    │  │ Loki     │  │Prometheus│  │ Custom  │ │
│  │(Traces)  │  │(Logs)    │  │(Metrics) │  │ APIs    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
└───────┼─────────────┼─────────────┼─────────────┼──────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                          │
                ┌─────────▼──────────┐
                │  Correlation Engine │
                │   Backend (FastAPI) │
                │  - Aggregates data  │
                │  - Correlates events│
                │  - Enriches context │
                └─────────┬───────────┘
                          │
                          │ HTTP/WebSocket/SSE
                          │
                ┌─────────▼──────────┐
                │  React Front-End   │
                │  - Real-time charts│
                │  - Time-series viz │
                │  - Dashboards      │
                └────────────────────┘
```

### Implementation Strategy

#### **1. Real-Time Data Fetching**

**Polling Strategy** (Currently stubbed in code):
```tsx
function CorrelationEnginePage() {
  const [stats, setStats] = useState<Stats>()
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesPoint[]>([])

  useEffect(() => {
    // Initial fetch
    fetchCurrentStats()
    fetchTimeSeries()

    // Poll every 15-30 seconds
    const statsInterval = setInterval(fetchCurrentStats, 15000)
    const seriesInterval = setInterval(fetchTimeSeries, 30000)

    return () => {
      clearInterval(statsInterval)
      clearInterval(seriesInterval)
    }
  }, [])

  const fetchCurrentStats = async () => {
    const data = await httpClient.get<Stats>('/correlation-engine/stats/current')
    setStats(data)
  }

  const fetchTimeSeries = async () => {
    const data = await httpClient.get<TimeSeriesPoint[]>(
      '/correlation-engine/stats/timeseries?window=30m'
    )
    setTimeSeriesData(data)
  }
}
```

**WebSocket Strategy** (Recommended for real-time):
```tsx
function useRealtimeMetrics() {
  const [metrics, setMetrics] = useState<Metrics>()

  useEffect(() => {
    const ws = new WebSocket('ws://api.example.com/metrics/stream')

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setMetrics(prev => ({
        ...prev,
        ...data
      }))
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      // Fallback to polling
    }

    return () => ws.close()
  }, [])

  return metrics
}
```

**Server-Sent Events (SSE)** (Alternative):
```tsx
function useSSEMetrics() {
  const [metrics, setMetrics] = useState<Metrics>()

  useEffect(() => {
    const eventSource = new EventSource('/correlation-engine/stream')

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setMetrics(data)
    }

    return () => eventSource.close()
  }, [])

  return metrics
}
```

#### **2. Backend Aggregation Endpoints**

**Proposed API Structure**:
```
GET  /correlation-engine/health
     Returns: { status: 'healthy' | 'degraded' | 'down', uptime: number }

GET  /correlation-engine/stats/current
     Returns: {
       requestsInQueue: number
       throughput: number
       errorRate: number
       droppedItems: number
       avgProcessingTime: number
       p95ProcessingTime: number
       otelSpansPerMin: number
       droppedSpansLastWindow: number
       lastUpdated: string
     }

GET  /correlation-engine/stats/timeseries?window=30m&interval=1m
     Returns: [
       { timestamp: '2025-12-11T14:00:00Z', requests: 1200, errors: 28 },
       { timestamp: '2025-12-11T14:01:00Z', requests: 1350, errors: 32 },
       ...
     ]

GET  /correlation-engine/incidents/recent?limit=10
     Returns: [
       {
         timestamp: string
         type: 'Timeout' | 'Parse Error' | '5xx' | ...
         service: string
         source: string
         traceId: string
         spanId: string
         logContext: {...}
       }
     ]

GET  /telemetry/traces?service=arda&limit=100
     Returns: Array of trace data from Tempo

GET  /telemetry/logs?service=arda&time_range=1h
     Returns: Array of log lines from Loki

GET  /telemetry/metrics?query=rate(requests_total[5m])
     Returns: Prometheus metric data
```

#### **3. Multi-Backend Data Aggregation**

**Backend Strategy** (FastAPI):
```python
@app.get("/correlation-engine/stats/current")
async def get_current_stats():
    # Fetch from multiple sources in parallel
    prometheus_task = fetch_prometheus_metrics()
    tempo_task = fetch_tempo_spans()
    loki_task = fetch_loki_logs()

    prometheus_data, tempo_data, loki_data = await asyncio.gather(
        prometheus_task, tempo_task, loki_task
    )

    # Correlate and aggregate
    return {
        "requestsInQueue": prometheus_data.queue_depth,
        "throughput": calculate_throughput(prometheus_data),
        "errorRate": calculate_error_rate(loki_data),
        "otelSpansPerMin": count_spans(tempo_data),
        "lastUpdated": datetime.utcnow().isoformat()
    }
```

#### **4. Visualization Components**

**Real-Time Line Chart** (Recharts):
```tsx
function RealtimeChart({ data }: { data: TimeSeriesPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(ts) => format(new Date(ts), 'HH:mm')}
        />
        <YAxis yAxisId="left" />
        <YAxis yAxisId="right" orientation="right" />
        <Tooltip
          labelFormatter={(ts) => format(new Date(ts), 'PPpp')}
        />
        <Legend />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="requests"
          stroke="#1B6AC7"
          name="Requests/min"
          dot={false}
          strokeWidth={2}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="errors"
          stroke="#F44336"
          name="Errors/min"
          dot={false}
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

**Heatmap for Error Distribution**:
```tsx
import { HeatMap } from '@nivo/heatmap'

function ErrorHeatmap({ data }: { data: HeatmapData[] }) {
  return (
    <HeatMap
      data={data}
      margin={{ top: 60, right: 90, bottom: 60, left: 90 }}
      valueFormat=">-.2s"
      axisTop={{
        tickSize: 5,
        tickPadding: 5,
        legend: 'Service',
        legendOffset: 46
      }}
      axisLeft={{
        tickSize: 5,
        tickPadding: 5,
        legend: 'Hour',
        legendOffset: -72
      }}
      colors={{
        type: 'diverging',
        scheme: 'red_yellow_green',
        divergeAt: 0.5
      }}
    />
  )
}
```

**Trace Waterfall Visualization**:
```tsx
function TraceWaterfall({ traceId }: { traceId: string }) {
  const [trace, setTrace] = useState<Trace>()

  useEffect(() => {
    fetch(`/telemetry/traces/${traceId}`)
      .then(res => res.json())
      .then(setTrace)
  }, [traceId])

  if (!trace) return <Loading />

  return (
    <div className="space-y-2">
      {trace.spans.map((span) => (
        <div
          key={span.spanId}
          className="relative h-8 bg-primary/20 rounded"
          style={{
            marginLeft: `${span.depth * 20}px`,
            width: `${(span.duration / trace.totalDuration) * 100}%`,
            left: `${(span.startTime / trace.totalDuration) * 100}%`
          }}
        >
          <div className="p-1 text-xs truncate">
            {span.operationName} ({span.duration}ms)
          </div>
        </div>
      ))}
    </div>
  )
}
```

#### **5. Time-Series Data Management**

**Sliding Window Buffer**:
```tsx
function useTimeSeriesBuffer(maxPoints: number = 30) {
  const [buffer, setBuffer] = useState<TimeSeriesPoint[]>([])

  const addPoint = useCallback((point: TimeSeriesPoint) => {
    setBuffer(prev => {
      const updated = [...prev, point]
      // Keep only last N points
      return updated.slice(-maxPoints)
    })
  }, [maxPoints])

  return { buffer, addPoint }
}

function Dashboard() {
  const { buffer, addPoint } = useTimeSeriesBuffer(30)

  useEffect(() => {
    const ws = new WebSocket('ws://api/metrics')
    ws.onmessage = (event) => {
      const point = JSON.parse(event.data)
      addPoint(point)
    }
    return () => ws.close()
  }, [addPoint])

  return <RealtimeChart data={buffer} />
}
```

#### **6. Advanced Visualization Features**

**Drill-Down Navigation**:
```tsx
function ClickableMetricCard({ metric }: { metric: Metric }) {
  const navigate = useNavigate()

  const handleDrillDown = () => {
    // Navigate to detailed view with filters
    navigate(`/telemetry/detail?service=${metric.service}&metric=${metric.name}`)
  }

  return (
    <KpiCard
      onClick={handleDrillDown}
      className="cursor-pointer"
      {...metric}
    />
  )
}
```

**Time Range Selector**:
```tsx
function TimeRangeSelector({ onChange }: { onChange: (range: TimeRange) => void }) {
  const presets = [
    { label: 'Last 15 min', value: '15m' },
    { label: 'Last 1 hour', value: '1h' },
    { label: 'Last 6 hours', value: '6h' },
    { label: 'Last 24 hours', value: '24h' },
    { label: 'Custom', value: 'custom' }
  ]

  return (
    <Select onValueChange={(val) => onChange(parseTimeRange(val))}>
      <SelectTrigger>
        <SelectValue placeholder="Select time range" />
      </SelectTrigger>
      <SelectContent>
        {presets.map(preset => (
          <SelectItem key={preset.value} value={preset.value}>
            {preset.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

**Metric Comparison**:
```tsx
function MetricComparison() {
  const [services, setServices] = useState(['arda', 'beorn'])
  const [metric, setMetric] = useState('error_rate')

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="timestamp" />
        <YAxis />
        <Tooltip />
        <Legend />
        {services.map((service, idx) => (
          <Line
            key={service}
            type="monotone"
            dataKey={service}
            stroke={COLORS[idx]}
            name={`${service} ${metric}`}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
```

#### **7. Error Correlation Visualization**

**Error Timeline with Correlated Events**:
```tsx
interface CorrelatedEvent {
  timestamp: string
  type: 'error' | 'trace' | 'log'
  service: string
  message: string
  correlationId: string
  relatedEvents: string[]  // IDs of related events
}

function CorrelationTimeline({ events }: { events: CorrelatedEvent[] }) {
  const [selectedEvent, setSelectedEvent] = useState<string>()

  return (
    <div className="relative">
      {/* Timeline axis */}
      <div className="absolute left-8 top-0 bottom-0 w-px bg-border" />

      {events.map((event, idx) => (
        <div
          key={event.correlationId}
          className={cn(
            "relative pl-16 pb-8",
            selectedEvent === event.correlationId && "bg-accent/10"
          )}
          onClick={() => setSelectedEvent(event.correlationId)}
        >
          {/* Timeline dot */}
          <div className={cn(
            "absolute left-6 w-4 h-4 rounded-full border-2",
            event.type === 'error' && "bg-destructive border-destructive",
            event.type === 'trace' && "bg-primary border-primary",
            event.type === 'log' && "bg-secondary border-secondary"
          )} />

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Badge variant={getBadgeVariant(event.type)}>
                  {event.type.toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {format(new Date(event.timestamp), 'PPpp')}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="font-semibold">{event.service}</div>
              <div className="text-sm text-muted-foreground">{event.message}</div>

              {/* Related events */}
              {event.relatedEvents.length > 0 && (
                <div className="mt-2 pt-2 border-t">
                  <div className="text-xs text-muted-foreground">
                    Correlated with {event.relatedEvents.length} other event(s)
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ))}
    </div>
  )
}
```

#### **8. Performance Optimization for Large Datasets**

**Virtual Scrolling** (for long lists):
```tsx
import { useVirtualizer } from '@tanstack/react-virtual'

function VirtualizedLogTable({ logs }: { logs: LogEntry[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: logs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,  // Row height
    overscan: 5
  })

  return (
    <div ref={parentRef} className="h-96 overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative'
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`
            }}
          >
            <LogRow log={logs[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Data Downsampling**:
```tsx
function downsampleTimeSeries(data: TimeSeriesPoint[], targetPoints: number): TimeSeriesPoint[] {
  if (data.length <= targetPoints) return data

  const factor = Math.ceil(data.length / targetPoints)
  return data.filter((_, idx) => idx % factor === 0)
}

function AdaptiveChart({ rawData }: { rawData: TimeSeriesPoint[] }) {
  // Downsample for large datasets
  const displayData = useMemo(() => {
    return rawData.length > 1000
      ? downsampleTimeSeries(rawData, 500)
      : rawData
  }, [rawData])

  return <LineChart data={displayData} />
}
```

**Lazy Loading Detail Views**:
```tsx
function LazyTraceDetail({ traceId }: { traceId: string }) {
  const [expanded, setExpanded] = useState(false)
  const [traceData, setTraceData] = useState<Trace>()

  useEffect(() => {
    if (expanded && !traceData) {
      fetch(`/telemetry/traces/${traceId}`)
        .then(res => res.json())
        .then(setTraceData)
    }
  }, [expanded, traceId, traceData])

  return (
    <div>
      <button onClick={() => setExpanded(!expanded)}>
        {expanded ? 'Hide' : 'Show'} Details
      </button>
      {expanded && traceData && <TraceWaterfall trace={traceData} />}
    </div>
  )
}
```

---

## Summary Comparison

### Current Architecture (With Grafana)

**Pros**:
- Grafana handles heavy visualization lifting
- No need to build custom chart components for traces/logs
- Powerful query languages (LogQL, TraceQL, PromQL)
- External deep-linking for investigation

**Cons**:
- Context switching between React app and Grafana
- Less customization control
- Requires user to learn Grafana UI

### Alternative Architecture (React-Only)

**Pros**:
- Unified user experience (no context switching)
- Full customization of visualizations
- Integrated correlation views (errors + traces + logs in one timeline)
- Better mobile experience

**Cons**:
- More development work (custom charts, time-series management)
- Performance challenges with large datasets
- Need to implement query interfaces for Tempo/Loki/Prometheus

---

## Technology Stack Summary

| Category | Technology | Purpose |
|----------|------------|---------|
| **Framework** | React 18.3 + TypeScript | UI library with type safety |
| **Build Tool** | Vite 5.4 | Fast dev server and optimized builds |
| **Routing** | React Router 6.26 | Client-side navigation |
| **State Management** | Zustand 4.5 | Lightweight global state |
| **Styling** | Tailwind CSS 3.4 | Utility-first CSS |
| **UI Components** | Radix UI | Accessible primitives |
| **Charts** | Recharts 3.5 | Responsive data visualization |
| **Icons** | Lucide React | Tree-shakeable SVG icons |
| **Date Handling** | date-fns | Date formatting utilities |
| **Markdown** | React Markdown | Content rendering |
| **Code Highlighting** | React Syntax Highlighter | Code block styling |

---

## Deployment Configuration

**Base Path**: `/correlation-station/`
**Dev Server**: `http://0.0.0.0:3000`
**Production Build**: `npm run build` → `/dist`
**API Proxy**: `/api` → `http://localhost:8080`

---

## Current Implementation Status

**Implemented**:
- Component architecture with Radix UI + Tailwind
- Zustand state management with persistence
- Mock dashboard with KPI cards
- Recharts visualization
- SECA error tracking interface
- Grafana deep-linking
- Authentication flow
- Tutorial progress tracking

**TODO** (Noted in code):
- API integration for `/correlation-engine/stats/current`
- Polling implementation for real-time updates
- Time-series data fetching
- WebSocket/SSE for live metrics
- Backend aggregation endpoints
- Error correlation logic

---

## Key Learnings & Recommendations

1. **Use Zustand for all global state** - Avoid Redux complexity
2. **Keep API data local to pages** - Only share when multiple pages need it
3. **Implement WebSocket for real-time** - Polling is inefficient for high-frequency updates
4. **Downsample large datasets** - Don't render 10,000 chart points
5. **Virtual scrolling for long lists** - Use `@tanstack/react-virtual`
6. **Memoize expensive computations** - Use `useMemo` for filtering/sorting
7. **Code split by route** - Use `React.lazy()` for page components
8. **Test on mobile** - Responsive design is critical for dashboards
9. **Add error boundaries** - Prevent full-page crashes
10. **Implement retry logic** - Network failures are common in observability tools

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     Browser (React SPA)                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Zustand Stores (Global State)                         │  │
│  │  - useAuth (localStorage)                              │  │
│  │  - useProgress (localStorage)                          │  │
│  └───────────────────┬────────────────────────────────────┘  │
│                      │                                        │
│  ┌───────────────────▼────────────────────────────────────┐  │
│  │  Component Tree                                        │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │ Layout (Header + Sidebar + Outlet)               │ │  │
│  │  │  ┌────────────────────────────────────────────┐  │ │  │
│  │  │  │ Page Components (Route-based)              │  │ │  │
│  │  │  │  - CorrelationEnginePage                   │  │ │  │
│  │  │  │  - SecaReviewsPage                         │  │ │  │
│  │  │  │  - LoginPage                               │  │ │  │
│  │  │  └────────────────────────────────────────────┘  │ │  │
│  │  │  ┌────────────────────────────────────────────┐  │ │  │
│  │  │  │ Molecules (KpiCard, Charts, Tables)        │  │ │  │
│  │  │  └────────────────────────────────────────────┘  │ │  │
│  │  │  ┌────────────────────────────────────────────┐  │ │  │
│  │  │  │ Atoms (Button, Badge, Card, Input)         │  │ │  │
│  │  │  └────────────────────────────────────────────┘  │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                              │
                         HTTP/WebSocket/SSE
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Correlation Engine)             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ API Endpoints                                          │  │
│  │ - /correlation-engine/stats/current                    │  │
│  │ - /correlation-engine/stats/timeseries                 │  │
│  │ - /correlation-engine/incidents/recent                 │  │
│  │ - /api/auth/login                                      │  │
│  └───────────────────┬────────────────────────────────────┘  │
│                      │                                        │
│  ┌───────────────────▼────────────────────────────────────┐  │
│  │ Data Aggregation Layer                                 │  │
│  │ - Correlates logs, traces, metrics                     │  │
│  │ - Enriches with context                                │  │
│  └───────────────────┬────────────────────────────────────┘  │
└────────────────────────┼───────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    Tempo     │ │     Loki     │ │  Prometheus  │
│   (Traces)   │ │    (Logs)    │ │  (Metrics)   │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## File Reference

**Key Implementation Files**:
- `/seefa-om/frontend/src/pages/CorrelationEnginePage.tsx:68-76` - Polling logic (stubbed)
- `/seefa-om/frontend/src/lib/auth.ts:20-76` - Zustand auth store
- `/seefa-om/frontend/src/lib/httpClient.ts:9-70` - HTTP client with error handling
- `/seefa-om/frontend/src/components/KpiCard.tsx:17-64` - Animated metric cards
- `/seefa-om/frontend/src/pages/SecaReviewsPage.tsx:240-253` - Recharts line chart
- `/seefa-om/frontend/vite.config.ts` - Build configuration
- `/seefa-om/frontend/tailwind.config.js` - Styling configuration

---

**Last Updated**: 2026-01-16
