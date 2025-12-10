# Correlation Enhancements Implementation

This document tracks the implementation of features from `.amazonq/rules/correlation-enhancemnets.md`.

## ✅ Completed Features

### Frontend (EPIC 1-2)

#### FE-1: Gateway Routing Error Handling
- **Status**: ✅ Complete
- **Files**:
  - `frontend/src/lib/httpClient.ts` - HTTP client with 502/404 detection
  - `frontend/src/components/ErrorBanner.tsx` - Error display component
- **Features**:
  - Detects 502 Bad Gateway and 404 HTML responses
  - Displays service name, route, and correlation ID
  - Provides retry and diagnostics links

#### FE-2: Datadog Modal Meme Image
- **Status**: ✅ Complete (already implemented)
- **Files**:
  - `frontend/src/pages/HomePage.tsx`
- **Features**:
  - Tim Robinson meme image in modal
  - Responsive image container
  - Fallback SVG if image fails to load

#### FE-6: Code Block Rendering
- **Status**: ✅ Complete
- **Files**:
  - `frontend/src/components/CodeBlock.tsx`
- **Features**:
  - Grafana-style syntax highlighting (black bg, orange keywords)
  - Copy-to-clipboard functionality
  - Supports LogQL, TraceQL, Python, YAML

### Backend (Redis & SECA Processing)

#### Redis Schema Implementation
- **Status**: ✅ Complete
- **Files**:
  - `correlation-engine/app/redis_schema.py`
- **Features**:
  - Circuit event indexing with correlation IDs
  - Trace and log file indexing
  - Traceback storage as Redis LISTs
  - Error grouping with SETs
  - TTL-based eviction (24-48h)
  - Error message normalization

#### SECA XLSX Processing
- **Status**: ✅ Complete
- **Files**:
  - `correlation-engine/app/seca_xlsx_processor.py` (existing, enhanced)
  - `correlation-engine/app/selenium_scraper.py` (new)
  - `correlation-engine/app/pdf_generator.py` (new)
  - `correlation-engine/app/routes/seca.py` (new)
- **Features**:
  - XLSX parsing with column mapping (D, E, G, J, S, W)
  - Selenium-based MDSO report scraping
  - Traceback extraction from logs
  - PDF report generation with error summaries
  - Amazon Q debug prompt generation
  - Reformatted XLSX with color-coded error groups
  - Redis integration for correlation caching

## 🚧 Pending Features

### Frontend (EPIC 3-5)

#### FE-3: User Login System
- **Status**: ⏳ Pending
- **Requirements**:
  - JWT or session-based authentication
  - Login/logout UI
  - Protected routes for tutorials and SECA reviews
  - User context/state management

#### FE-4: Onboarding Progress Tracker
- **Status**: ⏳ Pending
- **Requirements**:
  - Per-user tutorial completion tracking
  - "Mark Complete" buttons
  - Progress bar/checklist UI
  - Backend API for persistence

#### FE-5: Sidebar Navigation Conversion
- **Status**: ⏳ Pending
- **Requirements**:
  - Convert tutorial cards to left-hand sidebar
  - Collapsible sections (Logs, Traces, OTel, MDSO, SENSE)
  - Grafana Labs color palette
  - Active module highlighting
  - Mobile responsive

#### FE-7: Real-World Query Examples
- **Status**: ⏳ Pending
- **Requirements**:
  - Replace placeholder queries with real MDSO/SENSE examples
  - Pull from mdso-alloy/, mdso-instrumentation/, sense-apps/*/common/otel
  - Label examples by system

#### FE-8: Tutorial Video Embeds
- **Status**: ⏳ Pending
- **Requirements**:
  - YouTube player embedding
  - "Video coming soon" placeholder
  - Lazy loading
  - Specific videos:
    - LogQL: https://www.youtube.com/watch?v=57dQwcmqkpQ
    - TraceQL: https://www.youtube.com/watch?v=bgQblHktS78
    - Distributed Traces: https://www.youtube.com/watch?v=zDrA7Ly3ovU&t=2204s

#### FE-9: XLSX Upload UI
- **Status**: ⏳ Pending
- **Requirements**:
  - File upload drop zone
  - XLSX validation
  - Column preview mapping
  - Progress indicator

#### FE-10: Download Results UI
- **Status**: ⏳ Pending
- **Requirements**:
  - Processing status display
  - Auto-download PDF and XLSX
  - Summary screen with counts

### Backend

#### Horizontal Scaling
- **Status**: ⏳ Pending
- **Requirements**:
  - Redis configuration for correlation-engine
  - OTel Gateway → Correlation Engine → Redis flow
  - Queue backpressure prevention
  - Message schema normalization (msg vs message fields)

## 📋 Usage Examples

### Using the HTTP Client with Error Handling

```typescript
import { httpClient } from '@/lib/httpClient'
import ErrorBanner from '@/components/ErrorBanner'

try {
  const data = await httpClient.get('/correlation-engine/api/traces')
} catch (error) {
  return <ErrorBanner error={error} onRetry={() => fetchData()} />
}
```

### Using the CodeBlock Component

```typescript
import CodeBlock from '@/components/CodeBlock'

<CodeBlock 
  code='{service_name="api-gateway"} |= "error"'
  language="logql"
/>
```

### SECA XLSX Upload API

```bash
# Upload XLSX for processing
curl -X POST http://localhost:8000/seca/upload \
  -F "file=@seca_errors.xlsx"

# Response includes download URLs
{
  "status": "success",
  "total_errors": 150,
  "scraped_errors": 10,
  "error_groups": 5,
  "download_urls": {
    "pdf": "/seca/download/pdf?path=/tmp/report.pdf",
    "xlsx": "/seca/download/xlsx?path=/tmp/reformatted.xlsx"
  }
}
```

### Redis Correlation Storage

```python
from app.redis_schema import RedisCorrelationStore, CircuitEvent
import redis

# Initialize
client = redis.Redis(host='localhost', port=6379)
store = RedisCorrelationStore(client)

# Store circuit event
event = CircuitEvent(
    circuit_id="33.L1XX.801233..TWCC",
    date="2025-12-10_01-59-32",
    service_request_type="ACTIVATE",
    product_name="MDSO",
    error_message="Unable to connect to device",
    cdnc_summary="Connectivity check failed",
    status="FAIL"
)

correlation_id = store.store_circuit_event(event)

# Store traceback
store.store_traceback(correlation_id, [
    "Traceback (most recent call last):",
    "  File \"deviceconnectivitycheck.py\", line 58",
    "Exception: Unable to connect to device"
])

# Add to error group
normalized = store.normalize_error(event.error_message)
store.add_to_error_group(normalized, correlation_id)
```

## 🔧 Installation

### Frontend Dependencies

```bash
cd frontend
npm install
```

### Backend Dependencies

```bash
cd correlation-engine
pip install -r requirements.txt
```

### Selenium Setup

```bash
# Install Chrome/Chromium
# Ubuntu/Debian
sudo apt-get install chromium-browser chromium-chromedriver

# macOS
brew install --cask google-chrome
brew install chromedriver

# Windows
# Download from https://chromedriver.chromium.org/
```

## 🧪 Testing

### Test HTTP Error Handling

```bash
cd frontend
npm test -- httpClient.test.ts
```

### Test Redis Schema

```bash
cd correlation-engine
pytest tests/test_redis_schema.py
```

### Test SECA Processing

```bash
pytest tests/test_seca_processor.py
pytest tests/test_selenium_scraper.py
pytest tests/test_pdf_generator.py
```

## 📊 Architecture

### Data Flow

```
XLSX Upload
    ↓
Parse Circuit Errors
    ↓
Selenium Scraper → MDSO Reports (http://159.56.4.94/reports)
    ↓
Extract Tracebacks
    ↓
Store in Redis (correlation IDs, traces, error groups)
    ↓
Generate PDF Report + Reformatted XLSX
    ↓
Auto-Download to User
```

### Redis Keyspace

```
circuit:<correlation_id>        → HASH (circuit event data)
trace:<trace_id>                → HASH (trace metadata)
logfile:<log_filename>          → HASH (log file index)
traceback:<trace_id>            → LIST (traceback lines)
error_group:<normalized_error>  → SET (correlation IDs)
```

## 🚀 Next Steps

1. **Implement FE-3**: User authentication system
2. **Implement FE-4**: Tutorial progress tracking
3. **Implement FE-5**: Sidebar navigation
4. **Implement FE-9/10**: SECA upload UI in frontend
5. **Configure Redis**: Set up Redis cluster for horizontal scaling
6. **Deploy Selenium**: Containerize Selenium scraper
7. **Add monitoring**: Track SECA processing metrics

## 📝 Notes

- Redis TTL is set to 48 hours by default (configurable)
- Selenium scraper limits to 10 circuits per batch (configurable)
- PDF reports include first 10 detailed tracebacks
- Error normalization removes IPs, dates, and UUIDs for grouping
