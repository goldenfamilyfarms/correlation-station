import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { BookOpen, Video, FileText, PlayCircle, CheckCircle } from 'lucide-react'

interface Tutorial {
  id: string
  title: string
  description: string
  duration: string
  videoUrl?: string
  documentationSections: {
    title: string
    content: string
  }[]
  completed: boolean
}

const tutorials: Tutorial[] = [
  {
    id: 'getting-started',
    title: 'Getting Started with SEEFA Observability',
    description: 'Learn the basics of the SEEFA Observability platform and how to navigate the system',
    duration: '15 minutes',
    videoUrl: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    documentationSections: [
      {
        title: 'Platform Overview',
        content: `The SEEFA Observability platform is a comprehensive monitoring and correlation system that provides:

- **Real-time Log Aggregation**: Collect logs from all services using Grafana Loki
- **Distributed Tracing**: Track requests across services with Grafana Tempo
- **Metrics Collection**: Monitor system health with Prometheus
- **Correlation Engine**: Automatically link logs and traces for faster debugging

The platform is built on OpenTelemetry standards, ensuring compatibility with industry-standard tools and practices.`
      },
      {
        title: 'Key Components',
        content: `**Correlation Engine**
The heart of the system that links logs and traces based on trace_id within 60-second windows.

**Observability Stack**
- Grafana: Visualization and dashboards
- Loki: Log aggregation and querying
- Tempo: Distributed tracing
- Prometheus: Metrics storage
- Pyroscope: Continuous profiling

**Gateway**
OpenTelemetry Collector that routes telemetry data between applications and backends.`
      },
      {
        title: 'Getting Started Steps',
        content: `1. **Access Grafana**: Navigate to http://159.56.4.94:8443
2. **Explore Dashboards**: Review pre-built dashboards for system overview
3. **Query Logs**: Use the LogQL query interface to search logs
4. **View Traces**: Examine distributed traces in Tempo
5. **Set Up Alerts**: Configure alerts for critical conditions`
      }
    ],
    completed: false
  },
  {
    id: 'log-querying',
    title: 'Querying Logs with LogQL',
    description: 'Master LogQL to effectively search and analyze log data in Grafana Loki',
    duration: '20 minutes',
    videoUrl: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    documentationSections: [
      {
        title: 'LogQL Basics',
        content: `LogQL is Loki's query language, inspired by PromQL. It consists of two parts:

**Log Stream Selector**
Choose which log streams to query using labels:
\`\`\`
{ service_name="api-gateway" }
{ service_name="api-gateway", environment="production" }
\`\`\`

**Filter Expression**
Filter log lines within selected streams:
\`\`\`
{ service_name="api" } |= "error"
{ service_name="api" } |~ "error|timeout"
\`\`\``
      },
      {
        title: 'Common Query Patterns',
        content: `**Find errors in a service:**
\`\`\`
{ service_name="payment-service" } |= "error"
\`\`\`

**Count errors over time:**
\`\`\`
sum(count_over_time({ level="error" }[5m]))
\`\`\`

**Parse JSON logs:**
\`\`\`
{ service_name="api" } | json | level="error"
\`\`\`

**Extract metrics from logs:**
\`\`\`
avg_over_time({ service_name="api" } | json | unwrap duration [5m])
\`\`\``
      },
      {
        title: 'Best Practices',
        content: `1. **Use Label Selectors First**: Labels are indexed, making queries faster
2. **Chain Filters**: Multiple filters are processed left-to-right
3. **Parse Structured Logs**: Use \`| json\` or \`| logfmt\` for structured data
4. **Keep Label Cardinality Low**: Don't create labels for high-cardinality data
5. **Use Unwrap for Metrics**: Extract numeric values from logs for aggregation`
      }
    ],
    completed: false
  },
  {
    id: 'trace-analysis',
    title: 'Analyzing Distributed Traces',
    description: 'Learn how to use Grafana Tempo to debug distributed systems',
    duration: '25 minutes',
    videoUrl: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    documentationSections: [
      {
        title: 'Understanding Traces',
        content: `A trace represents a complete request journey through your distributed system.

**Trace Structure:**
- **Trace**: The complete journey of a request
- **Span**: A single operation within a trace
- **Attributes**: Key-value metadata on spans
- **Events**: Point-in-time occurrences within a span

**Key Concepts:**
- Parent-child relationships between spans
- Trace context propagation across services
- Span duration and latency analysis`
      },
      {
        title: 'Using TraceQL',
        content: `TraceQL is Tempo's query language for finding traces:

**Find slow traces:**
\`\`\`
{ duration > 1s }
\`\`\`

**Find traces with errors:**
\`\`\`
{ status = error }
\`\`\`

**Search by service:**
\`\`\`
{ .service.name = "payment-service" }
\`\`\`

**Complex queries:**
\`\`\`
{ .service.name = "api-gateway" && status = error && duration > 500ms }
\`\`\``
      },
      {
        title: 'Debugging with Traces',
        content: `**Step 1: Find the Trace**
Use TraceQL or correlate from logs to find the relevant trace

**Step 2: Analyze the Waterfall**
- Identify slow spans
- Look for gaps or delays
- Check span duration

**Step 3: Examine Attributes**
- HTTP status codes
- Database queries
- External API calls
- Error messages

**Step 4: Correlate with Logs**
Use the trace_id to find related logs for more context`
      }
    ],
    completed: false
  },
  {
    id: 'instrumentation',
    title: 'Instrumenting Applications',
    description: 'Add OpenTelemetry instrumentation to your services',
    duration: '30 minutes',
    videoUrl: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    documentationSections: [
      {
        title: 'OpenTelemetry Setup',
        content: `**Python (FastAPI) Setup:**
\`\`\`python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracer
trace.set_tracer_provider(TracerProvider())

# Instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
\`\`\`

**Environment Variables:**
\`\`\`bash
OTEL_SERVICE_NAME=my-service
OTEL_EXPORTER_OTLP_ENDPOINT=http://gateway:4318
\`\`\``
      },
      {
        title: 'Adding Custom Spans',
        content: `**Create Custom Spans:**
\`\`\`python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    with tracer.start_as_current_span("fetch_user") as span:
        span.set_attribute("user.id", user_id)
        user = await db.get_user(user_id)
        return user
\`\`\`

**Add Attributes:**
\`\`\`python
span.set_attribute("http.method", "GET")
span.set_attribute("user.email", email)
\`\`\``
      },
      {
        title: 'Best Practices',
        content: `**DO:**
- Use auto-instrumentation for frameworks
- Add custom spans for business operations
- Include meaningful attributes
- Use structured logging with trace_id
- Follow semantic conventions

**DON'T:**
- Add PII to span attributes
- Create too many spans (high cardinality)
- Forget error handling
- Block on span creation
- Hardcode endpoints`
      }
    ],
    completed: false
  },
  {
    id: 'seca-reviews',
    title: 'Creating SECA Error Reviews',
    description: 'Learn how to create and manage bi-weekly error reviews',
    duration: '15 minutes',
    documentationSections: [
      {
        title: 'What are SECA Reviews?',
        content: `SECA (System Error Compliance and Analysis) reviews are bi-weekly assessments that:

- **Track Error Trends**: Monitor error rates across services
- **Document Root Causes**: Capture detailed analysis of issues
- **Track Resolutions**: Follow action items to completion
- **Share Knowledge**: Distribute findings across teams

Reviews help maintain system reliability and improve team knowledge.`
      },
      {
        title: 'Creating a Review',
        content: `**Manual Creation:**
1. Navigate to SECA Reviews page
2. Click "Upload PDF/Markdown" button
3. Upload your error analysis document
4. Review extracted summary and errors
5. Edit as needed
6. Save the review

**Automated Upload:**
The system will extract:
- Executive summary
- Error details by service
- Severity levels
- Resolution status

You can edit any extracted data before saving.`
      },
      {
        title: 'Editing Reviews',
        content: `**Edit Summary:**
- Click "Edit" button in review header
- Update markdown content
- Click "Save" to persist changes

**Edit Error Cards:**
- Click edit icon on any error card
- Modify all fields including:
  - Error type and service
  - Severity and status
  - Description and root cause
  - Action items
  - Responsible team
- Click save icon to update

All changes are automatically timestamped.`
      }
    ],
    completed: false
  },
  {
    id: 'dashboards',
    title: 'Creating Grafana Dashboards',
    description: 'Build custom dashboards for your monitoring needs',
    duration: '25 minutes',
    videoUrl: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    documentationSections: [
      {
        title: 'Dashboard Basics',
        content: `**Dashboard Components:**
- **Panels**: Individual visualizations
- **Rows**: Organizational containers for panels
- **Variables**: Dynamic query parameters
- **Time Range**: Global time selector

**Panel Types:**
- Time Series: Line/area charts for metrics
- Stat: Single value displays
- Table: Tabular data
- Logs: Log stream viewer
- Trace: Trace viewer`
      },
      {
        title: 'Creating Panels',
        content: `**Steps:**
1. Click "Add Panel" in dashboard edit mode
2. Select visualization type
3. Choose data source (Prometheus, Loki, Tempo)
4. Write query (PromQL, LogQL, TraceQL)
5. Configure display options
6. Set thresholds and alerts
7. Save panel

**Example PromQL Query:**
\`\`\`
rate(http_requests_total[5m])
\`\`\``
      },
      {
        title: 'Best Practices',
        content: `**Dashboard Design:**
- Group related panels in rows
- Use consistent time ranges
- Add panel descriptions
- Use variables for flexibility
- Keep dashboards focused

**Performance:**
- Limit query time ranges
- Use appropriate refresh intervals
- Avoid too many panels
- Use efficient queries
- Consider query timeout settings`
      }
    ],
    completed: false
  }
]

export default function TutorialsPage() {
  const [selectedTutorial, setSelectedTutorial] = useState<Tutorial>(tutorials[0])
  const [completedTutorials, setCompletedTutorials] = useState<Set<string>>(new Set())

  const markComplete = (tutorialId: string) => {
    setCompletedTutorials(prev => new Set([...prev, tutorialId]))
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Onboarding Tutorials</h1>
        <p className="text-lg text-gray-600">
          Learn how to use the SEEFA Observability platform effectively
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Tutorials List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Available Tutorials</CardTitle>
              <CardDescription>
                {completedTutorials.size} of {tutorials.length} completed
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {tutorials.map((tutorial) => (
                <button
                  key={tutorial.id}
                  onClick={() => setSelectedTutorial(tutorial)}
                  className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                    selectedTutorial.id === tutorial.id
                      ? 'border-grafana-orange bg-grafana-orange/5'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-start gap-2">
                      <BookOpen className="h-4 w-4 text-grafana-orange mt-0.5 flex-shrink-0" />
                      <span className="font-semibold text-sm">{tutorial.title}</span>
                    </div>
                    {completedTutorials.has(tutorial.id) && (
                      <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-gray-500 ml-6">{tutorial.duration}</p>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Tutorial Content */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">{selectedTutorial.title}</CardTitle>
                  <CardDescription className="mt-2">
                    {selectedTutorial.description} • {selectedTutorial.duration}
                  </CardDescription>
                </div>
                {!completedTutorials.has(selectedTutorial.id) && (
                  <button
                    onClick={() => markComplete(selectedTutorial.id)}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors text-sm font-medium"
                  >
                    Mark Complete
                  </button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="video" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="video" disabled={!selectedTutorial.videoUrl}>
                    <Video className="h-4 w-4 mr-2" />
                    Video
                  </TabsTrigger>
                  <TabsTrigger value="documentation">
                    <FileText className="h-4 w-4 mr-2" />
                    Documentation
                  </TabsTrigger>
                </TabsList>

                {/* Video Tab */}
                <TabsContent value="video" className="space-y-4">
                  {selectedTutorial.videoUrl ? (
                    <div className="aspect-video bg-black rounded-lg overflow-hidden">
                      <iframe
                        src={selectedTutorial.videoUrl}
                        title={selectedTutorial.title}
                        className="w-full h-full"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                  ) : (
                    <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <PlayCircle className="h-16 w-16 text-gray-400 mx-auto mb-3" />
                        <p className="text-gray-500">Video coming soon</p>
                      </div>
                    </div>
                  )}

                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h3 className="font-semibold text-sm mb-2 text-blue-900">Quick Tips</h3>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• You can adjust playback speed in the video player</li>
                      <li>• Check the Documentation tab for written reference</li>
                      <li>• Practice the concepts in your own environment</li>
                    </ul>
                  </div>
                </TabsContent>

                {/* Documentation Tab */}
                <TabsContent value="documentation" className="space-y-4">
                  {selectedTutorial.documentationSections.map((section, idx) => (
                    <Card key={idx} className="border-2">
                      <CardHeader>
                        <CardTitle className="text-lg">{section.title}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="prose max-w-none">
                          <div className="whitespace-pre-wrap text-sm text-gray-700">
                            {section.content}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}