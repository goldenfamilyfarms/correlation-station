import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  GraduationCap, 
  Play, 
  CheckCircle2, 
  Circle, 
  Clock,
  ExternalLink,
  ChevronRight
} from 'lucide-react'
import CodeBlock from '@/components/CodeBlock'

interface Lesson {
  id: string
  title: string
  video_url?: string
  content_md: string
  order: number
}

interface Module {
  id: string
  slug: string
  title: string
  description: string
  order: number
  lessons: Lesson[]
}

type ProgressStatus = 'not_started' | 'in_progress' | 'completed'

interface LessonProgress {
  lesson_id: string
  status: ProgressStatus
  last_viewed_at?: string
  completed_at?: string
}

// Module definitions per blueprint
const modules: Module[] = [
  {
    id: 'grafana-101',
    slug: 'grafana-101',
    title: 'Grafana 101',
    description: 'Learn the fundamentals of Grafana, Loki, Tempo, Prometheus, Pyroscope, and Mimir',
    order: 1,
    lessons: [
      {
        id: 'grafana-basics',
        title: 'Grafana Basics',
        video_url: 'https://www.youtube.com/watch?v=grafana-basics',
        content_md: `# Grafana Basics

Grafana is our unified observability platform. Learn how to navigate dashboards and query data.

## Key Concepts

- **Dashboards**: Visual representations of metrics, logs, and traces
- **Data Sources**: Loki (logs), Tempo (traces), Prometheus (metrics)
- **Panels**: Individual visualizations (graphs, tables, stat panels)

## Our Dashboards

- [Correlation Engine Dashboard](http://159.56.4.94:3000/d/correlation-engine)
- [Sense Apps Overview](http://159.56.4.94:3000/d/sense-apps)
- [MDSO Telemetry](http://159.56.4.94:3000/d/mdso-telemetry)`,
        order: 1,
      },
      {
        id: 'loki-tempo',
        title: 'Logs & Traces (Loki/Tempo)',
        video_url: 'https://www.youtube.com/watch?v=loki-tempo',
        content_md: `# Logs & Traces with Loki and Tempo

Understanding how logs and traces work together in our observability stack.

## Loki - Log Aggregation

Loki stores logs from all our services. Use LogQL to query:

\`\`\`logql
{service="arda"} |= "error" | json | line_format "{{.timestamp}}: {{.message}}"
\`\`\`

## Tempo - Distributed Tracing

Tempo stores traces showing request flow across services. Use TraceQL:

\`\`\`traceql
{ .service.name = "arda" && status = error && duration > 500ms }
\`\`\`

## Trace-to-Log Correlation

In Grafana, you can jump from a trace span to related logs using trace_id.`,
        order: 2,
      },
    ],
  },
  {
    id: 'observability-101',
    slug: 'observability-101',
    title: 'Observability 101',
    description: 'Concepts: logs/metrics/traces/profiles, agents, OTel, Alloy, Collectors',
    order: 2,
    lessons: [
      {
        id: 'three-pillars',
        title: 'The Three Pillars of Observability',
        video_url: 'https://www.youtube.com/watch?v=three-pillars',
        content_md: `# The Three Pillars of Observability

## Logs
Events that happened at a point in time. Answer: "What happened?"

## Metrics
Numerical measurements over time. Answer: "How many? How fast?"

## Traces
Request flow through distributed systems. Answer: "Where did it go?"

## Profiles
Code-level performance data. Answer: "Why is it slow?"`,
        order: 1,
      },
      {
        id: 'otel-alloy',
        title: 'OpenTelemetry & Grafana Alloy',
        video_url: 'https://www.youtube.com/watch?v=otel-alloy',
        content_md: `# OpenTelemetry & Grafana Alloy

## OpenTelemetry (OTel)

Standard for instrumenting applications. Provides:
- Traces (spans)
- Metrics
- Logs

## Grafana Alloy

Agent that collects telemetry and forwards to backends. On MDSO, it:
- Tails log files from host filesystem
- Exports OTLP to OTEL Collector
- No container modifications needed`,
        order: 2,
      },
    ],
  },
  {
    id: 'getting-set-up',
    slug: 'getting-set-up',
    title: 'Getting Set Up',
    description: 'Access to WebEx, Jira, repos, internal tools. Team expectations and workflows.',
    order: 3,
    lessons: [
      {
        id: 'day-one',
        title: 'Day One Setup',
        video_url: '',
        content_md: `# Getting Set Up

## Access Requirements

- **WebEx**: Team meetings and collaboration
- **Jira**: Ticket tracking and sprint management
- **GitLab**: Code repositories
- **Grafana**: Observability dashboards
- **META Server**: Development environment

## Team Calendar

Find our team calendar in Outlook. Regular meetings:
- Daily standup: 9:00 AM
- Sprint planning: Every 2 weeks
- SECA Review: Bi-weekly

## Creating Tickets

1. Go to Jira
2. Create ticket in SEEFA project
3. Assign to appropriate team
4. Link to related tickets/epics

## Opening Merge Requests

1. Create feature branch
2. Make changes
3. Push to GitLab
4. Create MR targeting \`develop\`
5. Request review from team`,
        order: 1,
      },
    ],
  },
  {
    id: 'python-basics',
    slug: 'python-basics',
    title: 'Python Basics',
    description: 'Target: intern-level dev. Syntax, functions, requests, JSON. Example scripts hitting internal APIs.',
    order: 4,
    lessons: [
      {
        id: 'python-syntax',
        title: 'Python Syntax & Functions',
        video_url: 'https://www.youtube.com/watch?v=python-basics',
        content_md: `# Python Basics

## Basic Syntax

\`\`\`python
# Variables
circuit_id = "33.L1XX.801233..TWCC"
error_count = 42

# Functions
def check_circuit_status(circuit_id: str) -> dict:
    """Check status of a circuit"""
    return {"status": "active", "circuit_id": circuit_id}
\`\`\`

## Working with APIs

\`\`\`python
import requests

# GET request
response = requests.get("http://159.56.4.94:8080/api/circuit/status")
data = response.json()

# POST request
response = requests.post(
    "http://159.56.4.94:8080/api/circuit/create",
    json={"circuit_id": "33.L1XX.801233..TWCC"}
)
\`\`\``,
        order: 1,
      },
    ],
  },
  {
    id: 'linux-basics',
    slug: 'linux-basics',
    title: 'Linux Basics',
    description: 'Navigating, permissions, SSH, viewing logs, grep/tail/less. Real workflows.',
    order: 5,
    lessons: [
      {
        id: 'linux-commands',
        title: 'Essential Linux Commands',
        video_url: '',
        content_md: `# Linux Basics for Observability

## Navigating the Filesystem

\`\`\`bash
# Change directory
cd /var/log/correlation-engine

# List files
ls -lah

# Find files
find . -name "*.log" -type f
\`\`\`

## Viewing Logs

\`\`\`bash
# Tail logs (follow)
tail -f correlation-engine.log

# Grep for errors
grep -i "error" correlation-engine.log

# Less (scrollable)
less correlation-engine.log
\`\`\`

## Checking Service Status

\`\`\`bash
# Systemd service status
systemctl status correlation-engine

# Docker container logs
docker logs correlation-engine
\`\`\``,
        order: 1,
      },
    ],
  },
  {
    id: 'sense-mdso-fundamentals',
    slug: 'sense-mdso-fundamentals',
    title: 'Sense & MDSO Fundamentals',
    description: 'What they are. Local dev env setup. Creating products. Troubleshooting.',
    order: 6,
    lessons: [
      {
        id: 'sense-overview',
        title: 'Sense Applications Overview',
        video_url: '',
        content_md: `# Sense & MDSO Fundamentals

## What is Sense?

Service Engineering Automation - Three microservices:
- **ARDA**: Circuit design and validation
- **BEORN**: Eligibility checks and script planning
- **PALANTIR**: Device provisioning and configuration

## What is MDSO?

Multi-Domain Service Orchestrator - Manages product lifecycle from order to decommission.

## Local Development Setup

\`\`\`bash
# Clone Sense repos
git clone https://gitlab.com/service-engineering-automation/sense/arda.git
git clone https://gitlab.com/service-engineering-automation/sense/beorn.git
git clone https://gitlab.com/service-engineering-automation/sense/palantir.git

# Install dependencies
cd arda
pip install -r requirements.txt

# Run locally
python -m arda_app.main
\`\`\`

## Creating a Product in MDSO

1. Navigate to MDSO UI
2. Create new product order
3. Fill in service details
4. Submit for orchestration`,
        order: 1,
      },
    ],
  },
  {
    id: 'repos-workflows',
    slug: 'repos-workflows',
    title: 'Repos, APIs & Workflows',
    description: 'Tour of Palantir, Beorn, Arda. Core endpoints. Ticket → design → code → MR → deploy → observability → SECA.',
    order: 7,
    lessons: [
      {
        id: 'workflow-tour',
        title: 'Development Workflow Tour',
        video_url: '',
        content_md: `# Repos, APIs & Workflows

## Repository Tour

### ARDA
- **Repo**: \`service-engineering-automation/sense/arda\`
- **Main API**: Circuit design endpoints
- **Key Endpoints**:
  - \`POST /api/v1/circuit/create\`
  - \`GET /api/v1/circuit/{circuit_id}/status\`

### BEORN
- **Repo**: \`service-engineering-automation/sense/beorn\`
- **Main API**: Eligibility and script planning
- **Key Endpoints**:
  - \`POST /api/v1/eligibility/check\`
  - \`GET /api/v1/scriptplan/{circuit_id}\`

### PALANTIR
- **Repo**: \`service-engineering-automation/sense/palantir\`
- **Main API**: Device provisioning
- **Key Endpoints**:
  - \`POST /api/v1/provision/{circuit_id}\`

## Complete Workflow

1. **Ticket Created** (Jira)
2. **Design** (Architecture review)
3. **Code** (Feature branch, implement)
4. **MR** (Merge request, code review)
5. **Deploy** (GitLab CI/CD → META)
6. **Observability** (Monitor in Grafana)
7. **SECA** (Weekly error review)`,
        order: 1,
      },
    ],
  },
  {
    id: 'advanced-automation',
    slug: 'advanced-automation',
    title: 'Advanced Automation & Tools',
    description: 'Deeper dives into SECA workflows, Meta Web Tool, Correlation Engine, performance best practices.',
    order: 8,
    lessons: [
      {
        id: 'seca-deep-dive',
        title: 'SECA Workflows Deep Dive',
        video_url: '',
        content_md: `# Advanced Automation & Tools

## SECA Workflow

1. **Export XLSX** from MDSO
2. **Upload** to Correlation Station
3. **Automated Processing**:
   - Parse XLSX
   - Selenium scrapes Meta Web Tool
   - Extract tracebacks
   - Generate PDF with Amazon Q prompts
4. **Review** in SECA Review page
5. **Resolution** tracking

## Meta Web Tool

Access: http://159.56.4.94/reports

Contains detailed error logs and tracebacks for each circuit failure.

## Correlation Engine Best Practices

- Monitor queue depth
- Check Redis memory usage
- Review dropped spans
- Analyze error rates`,
        order: 1,
      },
    ],
  },
]

export default function NetDev101Page() {
  const [progress, setProgress] = useState<Record<string, LessonProgress>>({})
  const [expandedModule, setExpandedModule] = useState<string | null>(modules[0].id)
  const [selectedLesson, setSelectedLesson] = useState<string | null>(null)

  // Load progress from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('netdev101-progress')
    if (saved) {
      try {
        setProgress(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to load progress', e)
      }
    }
  }, [])

  // Save progress to localStorage
  const updateProgress = (lessonId: string, status: ProgressStatus) => {
    const newProgress = {
      ...progress,
      [lessonId]: {
        lesson_id: lessonId,
        status,
        last_viewed_at: new Date().toISOString(),
        completed_at: status === 'completed' ? new Date().toISOString() : undefined,
      },
    }
    setProgress(newProgress)
    localStorage.setItem('netdev101-progress', JSON.stringify(newProgress))
  }

  const getLessonProgress = (lessonId: string): ProgressStatus => {
    return progress[lessonId]?.status || 'not_started'
  }

  const getModuleProgress = (module: Module) => {
    const lessonStatuses = module.lessons.map((lesson) => getLessonProgress(lesson.id))
    const completed = lessonStatuses.filter((s) => s === 'completed').length
    const inProgress = lessonStatuses.filter((s) => s === 'in_progress').length
    return {
      completed,
      inProgress,
      total: module.lessons.length,
      percentage: Math.round((completed / module.lessons.length) * 100),
    }
  }

  const getStatusIcon = (status: ProgressStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'in_progress':
        return <Clock className="h-5 w-5 text-[#FF9800] animate-spin" />
      default:
        return <Circle className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getStatusBadge = (status: ProgressStatus) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-500">Completed</Badge>
      case 'in_progress':
        return <Badge className="bg-[#FFF3E0] text-foreground">In Progress</Badge>
      default:
        return <Badge variant="outline">Not Started</Badge>
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">NetDev101</h1>
        <p className="text-muted-foreground">
          Onboarding & training hub for observability and automation
        </p>
      </div>

      {/* Modules List */}
      <div className="space-y-4">
        {modules.map((module) => {
          const moduleProgress = getModuleProgress(module)
          const isExpanded = expandedModule === module.id

          return (
            <Card key={module.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-10 h-10 rounded-lg bg-[#FFF3E0] flex items-center justify-center">
                        <GraduationCap className="h-5 w-5 text-[#FF9800]" />
                      </div>
                      <div>
                        <CardTitle>{module.title}</CardTitle>
                        <CardDescription className="mt-1">{module.description}</CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 mt-3">
                      <div className="text-sm text-muted-foreground">
                        {moduleProgress.completed} / {moduleProgress.total} lessons completed
                      </div>
                      <div className="flex-1 max-w-xs">
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${moduleProgress.percentage}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-sm font-medium">{moduleProgress.percentage}%</div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedModule(isExpanded ? null : module.id)}
                  >
                    <ChevronRight
                      className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                    />
                  </Button>
                </div>
              </CardHeader>
              {isExpanded && (
                <CardContent>
                  <div className="space-y-3">
                    {module.lessons.map((lesson) => {
                      const lessonStatus = getLessonProgress(lesson.id)
                      const isSelected = selectedLesson === lesson.id

                      return (
                        <div key={lesson.id}>
                          <div
                            className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                              isSelected ? 'bg-primary/10' : 'hover:bg-muted'
                            }`}
                            onClick={() => setSelectedLesson(isSelected ? null : lesson.id)}
                          >
                            <div className="flex-shrink-0">
                              {getStatusIcon(lessonStatus)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="font-medium">{lesson.title}</div>
                              {lesson.video_url && (
                                <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                                  <Play className="h-3 w-3" />
                                  Video available
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {getStatusBadge(lessonStatus)}
                              <ChevronRight
                                className={`h-4 w-4 transition-transform ${isSelected ? 'rotate-90' : ''}`}
                              />
                            </div>
                          </div>

                          {isSelected && (
                            <Card className="mt-2 ml-8 bg-muted/50">
                              <CardContent className="pt-6">
                                <div className="space-y-4">
                                  {lesson.video_url && (
                                    <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
                                      <div className="text-center">
                                        <Play className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                                        <p className="text-sm text-muted-foreground">
                                          Video: {lesson.video_url}
                                        </p>
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          className="mt-2"
                                          asChild
                                        >
                                          <a href={lesson.video_url} target="_blank" rel="noopener noreferrer">
                                            Watch on YouTube <ExternalLink className="h-3 w-3 ml-1" />
                                          </a>
                                        </Button>
                                      </div>
                                    </div>
                                  )}

                                  <div className="prose prose-sm dark:prose-invert max-w-none">
                                    {lesson.content_md.split('\n').map((line, idx) => {
                                      if (line.startsWith('```')) {
                                        const lang = line.slice(3).trim()
                                        const codeStart = idx + 1
                                        const codeEnd = lesson.content_md.split('\n').findIndex(
                                          (l, i) => i > codeStart && l.startsWith('```')
                                        )
                                        const code = lesson.content_md
                                          .split('\n')
                                          .slice(codeStart, codeEnd)
                                          .join('\n')
                                        return (
                                          <CodeBlock key={idx} code={code} language={lang || 'text'} />
                                        )
                                      }
                                      if (line.startsWith('#')) {
                                        const level = line.match(/^#+/)?.[0].length || 1
                                        const text = line.replace(/^#+\s/, '')
                                        const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements
                                        return <HeadingTag key={idx} className="font-bold mt-4 mb-2">{text}</HeadingTag>
                                      }
                                      if (line.trim() === '') {
                                        return <br key={idx} />
                                      }
                                      return <p key={idx}>{line}</p>
                                    })}
                                  </div>

                                  <div className="flex gap-2 pt-4 border-t">
                                    {lessonStatus === 'not_started' && (
                                      <Button
                                        size="sm"
                                        onClick={() => updateProgress(lesson.id, 'in_progress')}
                                      >
                                        Start Lesson
                                      </Button>
                                    )}
                                    {lessonStatus === 'in_progress' && (
                                      <>
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          onClick={() => updateProgress(lesson.id, 'not_started')}
                                        >
                                          Mark Not Started
                                        </Button>
                                        <Button
                                          size="sm"
                                          onClick={() => updateProgress(lesson.id, 'completed')}
                                        >
                                          Mark Complete
                                        </Button>
                                      </>
                                    )}
                                    {lessonStatus === 'completed' && (
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => updateProgress(lesson.id, 'in_progress')}
                                      >
                                        Mark In Progress
                                      </Button>
                                    )}
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}

