import { useState } from 'react'
import { CheckCircle2, Circle, ChevronDown, ChevronRight, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import CodeBlock from '@/components/CodeBlock'
import { useAuth } from '@/lib/auth'
import { useProgress } from '@/lib/progress'

interface Tutorial {
  id: string
  title: string
  category: string
  videoUrl?: string
  content: string
}

const tutorials: Tutorial[] = [
  {
    id: 'logql-basics',
    title: 'LogQL Basics',
    category: 'Logs',
    videoUrl: 'https://www.youtube.com/embed/57dQwcmqkpQ',
    content: `# LogQL Query Language

LogQL is Loki's query language for querying logs. Here are real examples from MDSO:

## MDSO Circuit Creation Logs
\`\`\`logql
{service_name="arda"} |= "circuit_id" | json | circuit_id != ""
\`\`\`

## SENSE Device Errors
\`\`\`logql
{service_name="beorn"} |= "error" | json | level="ERROR"
\`\`\`

## Count Errors Over Time
\`\`\`logql
sum(count_over_time({service_name=~"arda|beorn|palantir"} |= "error" [5m]))
\`\`\``
  },
  {
    id: 'traceql-basics',
    title: 'TraceQL Basics',
    category: 'Traces',
    videoUrl: 'https://www.youtube.com/embed/bgQblHktS78',
    content: `# TraceQL Query Language

TraceQL queries distributed traces in Tempo. Real MDSO examples:

## Find Slow Circuit Operations
\`\`\`traceql
{ .service.name = "arda" && duration > 30s }
\`\`\`

## Device Connectivity Failures
\`\`\`traceql
{ .service.name = "palantir" && status = error && .operation = "device_check" }
\`\`\`

## Trace All SENSE Operations
\`\`\`traceql
{ .service.name =~ "arda|beorn|palantir" && .circuit_id != "" }
\`\`\``
  },
  {
    id: 'distributed-traces',
    title: 'Distributed Traces',
    category: 'Traces',
    videoUrl: 'https://www.youtube.com/embed/zDrA7Ly3ovU?start=2204',
    content: `# Understanding Distributed Traces

Traces show the complete journey of a request through MDSO/SENSE systems.

## MDSO Circuit Flow
1. ARDA receives circuit creation request
2. BEORN validates eligibility
3. PALANTIR checks device compliance
4. ARDA provisions circuit

Each step is a span with timing and metadata.`
  },
  {
    id: 'otel-mdso',
    title: 'MDSO Instrumentation',
    category: 'OpenTelemetry',
    content: `# MDSO OpenTelemetry Setup

Real configuration from mdso-alloy:

## Alloy Configuration
\`\`\`yaml
otelcol.receiver.otlp "mdso" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }
  output {
    traces  = [otelcol.processor.batch.default.input]
    logs    = [otelcol.processor.batch.default.input]
  }
}
\`\`\`

## Python Instrumentation (ARDA)
\`\`\`python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer("arda")

@app.post("/circuit/create")
async def create_circuit(circuit_data: dict):
    with tracer.start_as_current_span("create_circuit") as span:
        span.set_attribute("circuit.id", circuit_data["circuit_id"])
        span.set_attribute("circuit.type", circuit_data["service_type"])
        # Process circuit...
\`\`\``
  },
  {
    id: 'otel-sense',
    title: 'SENSE Instrumentation',
    category: 'OpenTelemetry',
    content: `# SENSE OpenTelemetry Setup

From sense-apps/arda/arda_app/common/otel:

## SENSE OTel Configuration
\`\`\`python
# sense-apps/arda/arda_app/common/otel/otel_sense.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
otlp_exporter = OTLPSpanExporter(
    endpoint="http://austx-mdso-logs-02.chtrse.com:4317",
    insecure=True
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
\`\`\`

## MDSO Pattern Extraction
\`\`\`python
# mdso-instrumentation/otel_instrumentation/mdso_patterns.py
CIRCUIT_ID_PATTERN = r'\\b\\d{2}\\.L[0-9A-Z]{3,4}\\.\\d{6}\\.\\.\\w{4}\\b'
\`\`\``
  },
  {
    id: 'mdso-queries',
    title: 'MDSO Log Queries',
    category: 'MDSO',
    content: `# MDSO-Specific Queries

## Find Circuit Creation Events
\`\`\`logql
{service_name="arda"} 
  |= "circuit_id" 
  | json 
  | circuit_id =~ "\\\\d{2}\\\\.L[0-9A-Z]{3,4}\\\\.\\\\d{6}\\\\.\\\\.\\\\.\\\\w{4}"
\`\`\`

## Track Device Provisioning
\`\`\`logql
{service_name="palantir"} 
  |= "device" 
  | json 
  | operation="provision" 
  | line_format "{{.timestamp}} {{.device_id}} {{.status}}"
\`\`\`

## Error Rate by Service
\`\`\`logql
sum by (service_name) (
  rate({service_name=~"arda|beorn|palantir"} |= "error" [5m])
)
\`\`\``
  },
  {
    id: 'sense-queries',
    title: 'SENSE Log Queries',
    category: 'SENSE',
    content: `# SENSE-Specific Queries

## BEORN Eligibility Checks
\`\`\`logql
{service_name="beorn"} 
  |= "eligibility" 
  | json 
  | circuit_id != "" 
  | eligible="true"
\`\`\`

## PALANTIR Compliance Validation
\`\`\`logql
{service_name="palantir"} 
  |= "compliance" 
  | json 
  | status="FAILED"
  | line_format "Circuit: {{.circuit_id}} - {{.failure_reason}}"
\`\`\`

## ARDA Circuit Status
\`\`\`logql
{service_name="arda"} 
  | json 
  | circuit_status != "" 
  | line_format "{{.circuit_id}}: {{.circuit_status}}"
\`\`\``
  }
]

const categories = ['Logs', 'Traces', 'OpenTelemetry', 'MDSO', 'SENSE']

export default function TutorialsPageNew() {
  const [selectedTutorial, setSelectedTutorial] = useState(tutorials[0])
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(categories))
  const { user } = useAuth()
  const { markComplete, isComplete, getProgress } = useProgress()

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  const handleMarkComplete = () => {
    if (user) {
      markComplete(user.id, selectedTutorial.id)
    }
  }

  const progress = user ? getProgress(user.id, tutorials.length) : 0

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white overflow-y-auto">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-grafana-orange">Tutorials</h2>
          {user && (
            <div className="mt-2">
              <div className="text-xs text-gray-400">Progress</div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-grafana-orange h-2 rounded-full transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs">{progress}%</span>
              </div>
            </div>
          )}
        </div>

        {categories.map(category => {
          const categoryTutorials = tutorials.filter(t => t.category === category)
          const isExpanded = expandedCategories.has(category)

          return (
            <div key={category}>
              <button
                onClick={() => toggleCategory(category)}
                className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-800 transition-colors"
              >
                <span className="font-medium">{category}</span>
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>

              {isExpanded && (
                <div className="bg-gray-800">
                  {categoryTutorials.map(tutorial => {
                    const completed = user ? isComplete(user.id, tutorial.id) : false
                    const isActive = selectedTutorial.id === tutorial.id

                    return (
                      <button
                        key={tutorial.id}
                        onClick={() => setSelectedTutorial(tutorial)}
                        className={`w-full px-6 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-700 transition-colors ${
                          isActive ? 'bg-gray-700 border-l-2 border-grafana-orange' : ''
                        }`}
                      >
                        {completed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                        ) : (
                          <Circle className="h-4 w-4 text-gray-500 flex-shrink-0" />
                        )}
                        <span className={completed ? 'text-green-400' : ''}>{tutorial.title}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto bg-white">
        <div className="max-w-4xl mx-auto p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-900">{selectedTutorial.title}</h1>
            {user && !isComplete(user.id, selectedTutorial.id) && (
              <Button onClick={handleMarkComplete} className="bg-grafana-orange hover:bg-grafana-orange/90">
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Mark Complete
              </Button>
            )}
          </div>

          {/* Video */}
          {selectedTutorial.videoUrl ? (
            <div className="mb-8 rounded-lg overflow-hidden shadow-lg">
              <iframe
                width="100%"
                height="450"
                src={selectedTutorial.videoUrl}
                title={selectedTutorial.title}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                loading="lazy"
              />
            </div>
          ) : (
            <div className="mb-8 bg-gray-100 rounded-lg p-12 text-center">
              <Play className="h-16 w-16 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 font-medium">Video coming soon</p>
            </div>
          )}

          {/* Content */}
          <div className="prose max-w-none">
            {selectedTutorial.content.split('\n\n').map((section, idx) => {
              if (section.startsWith('```')) {
                const lines = section.split('\n')
                const language = lines[0].replace('```', '')
                const code = lines.slice(1, -1).join('\n')
                return <CodeBlock key={idx} code={code} language={language} />
              }
              
              if (section.startsWith('# ')) {
                return <h1 key={idx} className="text-2xl font-bold mt-8 mb-4">{section.replace('# ', '')}</h1>
              }
              
              if (section.startsWith('## ')) {
                return <h2 key={idx} className="text-xl font-semibold mt-6 mb-3 text-grafana-orange">{section.replace('## ', '')}</h2>
              }
              
              return <p key={idx} className="mb-4 text-gray-700">{section}</p>
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
