# 🎓 Correlation Station UI - Observability Training Platform

An interactive React-based training portal for learning modern observability tools, monitoring practices, and distributed systems architecture.

## 🌟 Features

### 🏠 Homepage
- **Quick Access Dashboard**: Navigate to Grafana, Pyroscope, Prometheus, and Correlation Engine
- **DataDog Legacy Modal**: Fun interactive modal with Tim Robinson "Are you sure about that?" meme
- **Grafana Color Palette**: Beautiful light mode theme using official Grafana colors
- **Responsive Design**: Works on desktop, tablet, and mobile

### 📚 Documentation Hub
Comprehensive guides covering:

#### TraceQL (Trace Query Language)
- Basic syntax and query structure
- Common selectors (service.name, status, duration, etc.)
- Advanced filtering and aggregation
- Real-world query examples
- Pro tips and best practices

#### PromQL (Prometheus Query Language)
- Metric queries and label filtering
- Aggregation functions (sum, avg, rate, etc.)
- Histogram quantiles for percentiles
- Error rate calculations
- Time-series operations and offsets

#### Application Instrumentation
- Why instrumentation matters
- Python/FastAPI code examples
- Span creation and attribute setting
- Error handling patterns
- Semantic conventions

#### OpenTelemetry SDK
- SDK setup and configuration
- Environment variable reference
- Exporter options (OTLP, Jaeger, Zipkin, Console)
- TracerProvider and SpanProcessor
- Production deployment tips

### 🏗️ Architecture Page
Detailed system architecture documentation:

- **High-Level Diagrams**: ASCII art showing LGTM stack flow
- **Service Breakdown**: In-depth details on each component
  - Grafana 10.2.0 (visualization)
  - Loki 2.9.2 (log aggregation)
  - Tempo 2.3.0 (distributed tracing)
  - Prometheus 2.48.0 (metrics)
  - Pyroscope (continuous profiling)
- **Data Flow**: Step-by-step telemetry journey
- **Design Principles**: Low cardinality, vendor neutrality, correlation-first
- **Network Topology**: Port mappings and internal routing

### 🔍 SECA Error Reviews
Bi-weekly error analysis and tracking system:

#### Features
- **Review Timeline**: Organized by week with creation/update timestamps
- **Error Cards**: Rich detail cards for each error including:
  - Severity badges (Critical, High, Medium, Low)
  - Status indicators (Resolved, In Progress, Planned, Investigating)
  - Service name and occurrence count
  - Trend arrows (increasing/decreasing)
- **Root Cause Analysis**: Detailed explanation of what went wrong
- **Action Items**: Checklist of remediation steps
- **Team Assignment**: Responsible team for each error
- **Editable Summaries**: Update executive summaries directly in the UI

#### Sample Error Review
The system comes with a sample review showing realistic production errors:
- Database connection pool exhaustion (Critical - Resolved)
- Token refresh race condition (High - Resolved)
- API gateway 502 errors (High - In Progress)
- Memory leak investigation (Medium - Investigating)

## 🛠️ Technology Stack

### Frontend
- **React 18.3**: Latest React with hooks
- **TypeScript**: Type-safe development
- **Vite 5.4**: Lightning-fast build tool
- **Shadcn UI**: Beautiful, accessible components built on Radix UI
- **Tailwind CSS**: Utility-first styling
- **React Router 6**: Modern client-side routing
- **Lucide Icons**: Consistent icon system
- **date-fns**: Date formatting and manipulation

### Backend API
- **FastAPI**: High-performance Python web framework
- **aiosqlite**: Async SQLite for SECA reviews database
- **Pydantic**: Request/response validation
- **SQLite**: Lightweight database for review storage

### Deployment
- **Docker Multi-Stage Build**: Optimized production images
- **Nginx**: Static file serving and API proxying
- **Docker Compose**: Orchestration with correlation engine

## 🚀 Quick Start

### Development Mode

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (with hot reload)
npm run dev

# Access at http://localhost:3000
# API requests proxied to http://correlation-engine:8080
```

### Production Build

```bash
# Build optimized bundle
npm run build

# Preview production build
npm run preview
```

### Docker Deployment

```bash
# Build and run with docker-compose
cd ..  # Back to seefa-om root
docker-compose up -d correlation-station-ui

# Access at http://localhost:3000
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # Shadcn UI components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── tabs.tsx
│   │   │   └── separator.tsx
│   │   └── Layout.tsx       # Main layout with navigation
│   ├── pages/
│   │   ├── HomePage.tsx               # Landing page with quick links
│   │   ├── DocumentationPage.tsx     # TraceQL, PromQL, instrumentation
│   │   ├── ArchitecturePage.tsx      # System architecture docs
│   │   └── SecaReviewsPage.tsx       # Error review dashboard
│   ├── lib/
│   │   └── utils.ts         # Utility functions (cn, etc.)
│   ├── App.tsx              # Router configuration
│   ├── main.tsx             # React entry point
│   └── index.css            # Global styles & Tailwind
├── public/
├── Dockerfile               # Multi-stage production build
├── nginx.conf               # Nginx reverse proxy config
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js       # Grafana color theme
```

## 🎨 Grafana Color Palette

The UI uses the official Grafana color scheme:

```css
--grafana-orange: #FF7E27  /* Primary brand color */
--grafana-blue: #33A2E5    /* Secondary actions */
--grafana-green: #3EB15B   /* Success states */
--grafana-yellow: #F2CC0C  /* Warning states */
--grafana-red: #E02F44     /* Error states */
--grafana-purple: #9664D9  /* Accent color */
```

## 🔌 API Integration

### Endpoints Used

The frontend communicates with the correlation engine API:

```typescript
// SECA Reviews
GET    /api/seca-reviews           // List all reviews
GET    /api/seca-reviews/:id       // Get specific review
POST   /api/seca-reviews           // Create new review
PUT    /api/seca-reviews/:id       // Update review summary
DELETE /api/seca-reviews/:id       // Delete review
```

### Data Models

```typescript
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
```

## 🌐 Nginx Configuration

The production build uses Nginx to:

1. **Serve static files** (React bundle, assets)
2. **Proxy API requests** to correlation-engine:8080
3. **Enable gzip compression** for faster loading
4. **Cache static assets** with 1-year expiry
5. **Handle SPA routing** (fallback to index.html)

```nginx
location /api {
    proxy_pass http://correlation-engine:8080;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 🎯 Key Features Explained

### DataDog Modal Easter Egg

When users click the DataDog card, they're greeted with:
- Tim Robinson "Are you sure about that?" meme
- Two buttons:
  - "Yes, I'm sure" → Opens DataDog (for legacy users)
  - "No, I'm sorry! I like cool OM tools" → Closes modal (promotes modern tools)

This adds humor while promoting the use of the LGTM stack over expensive proprietary solutions.

### Editable SECA Reviews

The SECA Reviews page allows authorized users to:
1. View historical error reviews by week
2. Click "Edit" to modify the executive summary
3. Updates are saved to SQLite database
4. Changes are timestamped (`updated_at`)

This enables the observability team to maintain living documentation of production issues.

### Responsive Documentation

All documentation pages use:
- **Tabs** for organizing related content
- **Code blocks** with syntax highlighting (gray-900 background)
- **Color-coded sections** (Grafana palette for visual hierarchy)
- **Collapsible cards** for detailed information
- **Copy-friendly** code snippets

## 📊 Sample Data

The system initializes with a sample SECA review containing realistic production errors:

**Week 46 - Nov 11-15, 2024**
- Database Connection Pool Exhaustion (Critical - 2,847 occurrences)
- Token Refresh Race Condition (High - 1,234 occurrences)
- 502 Bad Gateway During Spikes (High - 456 occurrences)
- Gradual Memory Leak (Medium - 12 occurrences)

Each error includes:
- Detailed root cause analysis
- Concrete action items
- Team assignments
- Resolution progress

## 🚢 Deployment Architecture

```
┌─────────────────────────────────────┐
│    Correlation Station UI (Nginx)   │
│                                     │
└──────────┬──────────────────────────┘
           │ Proxy /api/* requests
           ▼
┌─────────────────────────────────────┐
│    Correlation Engine (FastAPI)     
│  ┌───────────────────────────────┐  │
│  │   SQLite Database             │  │
│  │   /app/data/seca_reviews.db   │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Docker Volumes**:
- `seca-db:/app/data` - Persistent storage for SECA reviews

## 🔒 Security Considerations

1. **Input Validation**: All user inputs validated by Pydantic models
2. **SQL Injection**: Uses parameterized queries with aiosqlite
3. **XSS Prevention**: React escapes content by default
4. **CORS**: Configured in correlation engine to allow frontend origin
5. **Rate Limiting**: Consider adding nginx rate limiting in production

## 🎓 Training Use Cases

### For New Team Members
1. Start with **Documentation** tab to learn TraceQL and PromQL basics
2. Review **Architecture** page to understand system design
3. Explore **SECA Reviews** to see real-world error patterns

### For Experienced Engineers
1. Use **Documentation** as a quick reference for query syntax
2. Check **Architecture** for deployment details and port mappings
3. Contribute to **SECA Reviews** with weekly error analysis

### For Managers/Leadership
1. View **SECA Reviews** for error trends and team workload
2. Check **Architecture** for cost optimization opportunities (open-source stack)
3. Use **Homepage** quick links to monitor dashboards

## 📝 Contributing to Documentation

To add new documentation:

1. Edit `src/pages/DocumentationPage.tsx`
2. Add a new `<TabsContent>` section
3. Follow the existing structure:
   - Title with icon
   - What is it? (introduction)
   - Basic examples
   - Advanced examples
   - Pro tips

Example:
```tsx
<TabsContent value="new-topic">
  <Card>
    <CardHeader>
      <CardTitle>New Topic</CardTitle>
    </CardHeader>
    <CardContent>
      {/* Your content here */}
    </CardContent>
  </Card>
</TabsContent>
```

## 🐛 Troubleshooting

### Frontend not loading
```bash
# Check container logs
docker logs correlation-station-ui

# Rebuild
docker-compose build correlation-station-ui
docker-compose up -d correlation-station-ui
```

### API requests failing (404)
- Verify correlation engine is running: `docker ps | grep correlation-engine`
- Check nginx proxy configuration in `nginx.conf`
- Ensure CORS is enabled in `correlation-engine/app/main.py`

### SECA Reviews not loading
```bash
# Check database
docker exec -it correlation-engine sh
ls -la /app/data/seca_reviews.db

# Check API
curl http://localhost:8080/api/seca-reviews
```

### Build errors
```bash
# Clear node_modules
rm -rf frontend/node_modules
cd frontend && npm install

# Clear Docker build cache
docker-compose build --no-cache correlation-station-ui
```

## 🎯 Roadmap

Future enhancements:
- [ ] Dark mode toggle (Grafana dark theme)
- [ ] Interactive TraceQL/PromQL query builder
- [ ] SECA review comments and discussions
- [ ] Export reviews to PDF/Markdown
- [ ] Real-time error notifications via WebSocket
- [ ] User authentication and role-based access
- [ ] Metrics dashboard integration (Grafana embed)
- [ ] Service health status indicators

## 📚 Learning Resources

### External Documentation
- [Grafana Tempo Docs](https://grafana.com/docs/tempo/latest/)
- [TraceQL Reference](https://grafana.com/docs/tempo/latest/traceql/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Shadcn UI Components](https://ui.shadcn.com/)

### Internal Guides
- See `docs/` directory for architecture deep-dives
- Check `correlation-engine/README.md` for API details
- Review `k6/README.md` for load testing guides

## 🙏 Credits

Built with:
- **Grafana Labs** - LGTM stack and color palette
- **Shadcn** - Beautiful UI components
- **Radix UI** - Accessible component primitives
- **Tailwind CSS** - Utility-first CSS framework
- **Tim Robinson** - Meme inspiration

---

**Happy Learning! 🚀**

For questions or issues, check the main [README.md](README.md) or open an issue.
