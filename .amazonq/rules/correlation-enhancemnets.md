# **✅ Cleaned Master Prompt (Image-Free, Structured)**

# **Context**

I am building an internal Observability & Correlation platform integrating Grafana LGTM stack (Loki, Tempo, Prometheus, Pyroscope), OpenTelemetry, MDSO, SENSE, and a custom correlation engine.

I need help debugging backend access issues, implementing missing frontend features, improving onboarding/tutorial UX, and designing a Selenium-based automated error analysis pipeline.

# **1. Bug Fixes (Backend / Routing / Access)**

**Access Issues**

1. ARDA UI
    - URL: http://austx-mdso-logs-02.chtrse.com/arda
    - Error: 502 Bad Gateway
2. Correlation Engine Docs
    - URL: http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs
    - Error: 502 Bad Gateway

1. Pyroscope UI
    - Issue: “Failed to load app names”
    - Response: HTTP 404, HTML response instead of API JSON

# **2. Frontend Enhancements (Currently Missing)**

**Datadog Modal Enhancement**

- Replace placeholder text "ARE YOU SURE ABOUT THAT?!"
- Display Tim Robinson “Are you sure about that?” meme image
- Current implementation is text-only; needs image rendering

# **3. User Accounts & Progress Tracking**

- Add user authentication
- Users should:
    - Track onboarding module completion
    - Update SECA review data
    - Persist progress per-user
-

# **4. Tutorials UX Improvements**

**Navigation**

- Convert tutorial list into a left-hand side navigation menu
- Use Grafana Labs sidebar color scheme
- Support collapsible sections per module

**Documentation Formatting**

- Tutorials must render code blocks for:
    - LogQL
    - TraceQL
    - OpenTelemetry SDK examples
-
- Code blocks should match Grafana style:
    - Black background
    - Orange + white syntax text
-

**Example Content**

- Use real MDSO & SENSE queries
- OpenTelemetry examples must reference:
    - mdso-alloy/
    - mdso-instrumentation/
    - sense-apps/<app>/common/otel
-

# **5. Tutorial Media Rules**

- Grafana-related modules → Embed Grafana YouTube videos
- Non-Grafana modules → Show placeholder: “Video coming soon”

**Required Videos**

- LogQL: https://www.youtube.com/watch?v=57dQwcmqkpQ
- TraceQL: https://www.youtube.com/watch?v=bgQblHktS78
- Distributed Traces: https://www.youtube.com/watch?v=zDrA7Ly3ovU&t=2204s

# **6. SECA Review: XLSX Upload + Automated Error Analysis**

**XLSX Upload Requirements**

Extract and store:

- Circuit ID → Column D
- Date → Column S
- Service Request Type → Column J
- Product Name → Column G
- Error Message → Column E
- Initial CDNC Summary → Column W

Create dictionary key:

<circuit_id>_<date>

Example:

33.L1XX.801233..TWCC_2025-12-10_01-59-32

# **7. Selenium Automation Logic**

**Target Web Tool**

http://159.56.4.94/reports

**Workflow**

1. Navigate report tables:

/html/body/section/table/tbody

1.
2. For each product link:
    - Match circuit_id + date
    - Open link
    - Download and parse .txt logs
    - Extract Python traceback via regex
3.

**Traceback Example**

Traceback (most recent call last):

File "/bp2/data/contexts/201/model-definitions/scripts/common_plan.py", line 434, in run

response = self.process()

File "/bp2/data/contexts/201/model-definitions/scripts/deviceconfiguration/deviceconnectivitycheck.py", line 58, in process

raise Exception(f"Unable to connect to device at {device_ip}")

Exception: Unable to connect to device at CSTNOH122ZW.CML.CHTRSE.COM

# **8. orch_trace Handling**

If link contains orch_trace:

1. Find first "FAILED" entry
2. Extract log_file
3. Locate matching .txt
4. Parse traceback

Example JSON:

{

"state": "FAILED",

"log_file": "plan-script-...activate-2025-12-10T01:41:08.538Z",

"process": "scripts.deviceconfiguration.deviceconnectivitycheck.Activate",

"categorized_error": "MDSO | Process Error",

"resource_id": "4cbd1db2-d569-11f0-b4fc-fbbc1440290a"

}

# **9. Final Outputs (Auto-Download)**

**Output A: PDF Report**

- Selenium findings
- Errors grouped by type
- Generated Amazon Q debug prompt for VS Code

**Output B: Reformatted XLSX**

- Filter Column A = FAIL
- Hide Columns:

B, C, H, K, M, N, D, P, Q, R, S, T, X, AE, AF

-
- Sort Column E A → Z
- Highlight identical error groups with matching colors

# **10. Horizontal Scaling & Architecture**

**Redis**

- Configure Redis for correlation-engine caching
- Prevent queue backlog:

Alloy (MDSO) → OTel Gateway (META)

**Telemetry Flow**

Alloy → OTel Gateway → Correlation Engine → Redis

**Parsing Strategy**

- Validate spans, events, logs from:
    - MDSO
    - SENSE
-
- Define clear message schema
- Normalize msg and message fields

# **🖼 Image Descriptions (Converted to Text)**

**Image 1 – Meme**

A meme image of comedian Tim Robinson with the caption:

“YOU SURE ABOUT THAT?”

Used humorously to question using Datadog instead of open-source observability tools.

**Image 2 – Datadog Confirmation Modal**

A UI modal titled:

“Hold up! Are you sure you want to use DataDog?”

Includes:

- Large placeholder area labeled: “ARE YOU SURE ABOUT THAT?!”
- Text promoting open-source observability tools
- Two buttons:
    - ✅ “Yes, I’m sure (take me to Datadog)”
    - ✅ “No, I’m sorry! I like cool OM tools”
-

**Image 3 – Grafana Cloud Logs Documentation**

Grafana documentation showing:

- Left sidebar with Logs instrumentation
- Page titled “Send Logs to Grafana Cloud”
- Mentions using Grafana Alloy
- Labels-based log indexing

**Image 4 – LogQL Tutorial Page**

Tutorial titled:

“Querying Logs with LogQL”

Features:

- Left navigation with tutorials
- Code examples using:

{service_name="api-gateway"} |= "error"

-
- Emphasis on LogQL basics and common patterns

**Image 5 – TraceQL Documentation**

Grafana Tempo page titled:

“TraceQL – Trace Query Language”

Includes:

- Syntax examples:

{ .service.name = "auth-service" }

{ status = error }

{ duration > 1s }

Below is a clean, implementation-ready frontend task list followed by a Redis

# **✅ Frontend Task List (Implementation-Ready)**

# **EPIC 1 — Core UI Stability & Access Fixes**

**FE-1: Gateway Routing Error Handling**

Goal: Avoid silent failures when backend routes return 502/404

Tasks

- Add global HTTP error interceptor (Axios / Fetch wrapper)
- Detect:
    - 502 Bad Gateway
    - 404 HTML response (expected JSON)
-
- Display inline error banner with:
    - Service name
    - Route
    - Correlation ID (if present)
-
- Provide retry + diagnostics link

Acceptance Criteria

- Users see actionable error information
- No white-screen failures
- Errors are traceable to backend services

# **EPIC 2 — Datadog Confirmation Modal (UX + Branding)**

**FE-2: Meme Image Replacement**

Goal: Replace placeholder text with meme image

Tasks

- Replace text block with responsive <img> container
- Import Tim Robinson meme as static asset
- Ensure:
    - Alt text for accessibility
    - Proper scaling on mobile
-
- Retain CTA buttons unchanged

Acceptance Criteria

- Meme image renders reliably
- No layout shift
- Passes accessibility checks

# **EPIC 3 — Authentication & User Progress Tracking**

**FE-3: User Login System**

Goal: Enable per-user onboarding progress & reviews

Tasks

- Add auth flow (JWT or session-based)
- Login / logout UI
- Persist user ID in frontend context/state
- Protect tutorials + SECA review routes

Acceptance Criteria

- Users can log in/out
- Progress is user-scoped
- Refresh does not lose state

**FE-4: Onboarding Progress Tracker**

Goal: Track tutorial completion

Tasks

- Add progress state per module
- “Mark Complete” button per tutorial
- Visual progress bar / checklist
- Persist progress via backend API

Acceptance Criteria

- Progress persists across sessions
- Completed modules remain marked
- UI updates without reload

# **EPIC 4 — Tutorials UX & Documentation Styling**

**FE-5: Sidebar Navigation Conversion**

Goal: Replace tutorial cards with Grafana-style sidebar

Tasks

- Convert tutorial list into left-hand nav
- Support collapsible sections (Logs, Traces, OTel, MDSO, SENSE)
- Match Grafana Labs color palette
- Highlight active module

Acceptance Criteria

- Sidebar mirrors Grafana UX
- Navigation feels intuitive
- Mobile responsive

**FE-6: Code Block Rendering**

Goal: Match Grafana docs look and feel

Tasks

- Implement syntax-highlighted code blocks:
    - Black background
    - Orange keywords
    - White text
-
- Support:
    - LogQL
    - TraceQL
    - Python
    - YAML
-
- Use reusable <CodeBlock /> component

Acceptance Criteria

- Code blocks match Grafana docs visually
- Copy-to-clipboard supported
- No Markdown rendering issues

**FE-7: Real-World Query Examples**

Goal: Teach with actual MDSO/SENSE queries

Tasks

- Replace placeholder queries
- Pull examples from:
    - mdso-alloy/
    - mdso-instrumentation/
    - sense-apps/*/common/otel
-
- Label examples clearly by system

Acceptance Criteria

- All examples are real and relevant
- No fake/demo queries remain

**FE-8: Tutorial Video Embeds**

Goal: Consistent media behavior

Tasks

- Embed YouTube player when video is available
- Show placeholder card (“Video coming soon”) when not
- Lazy-load videos

Acceptance Criteria

- Grafana tutorials show videos
- Non-Grafana modules show placeholder
- No layout jumping

# **EPIC 5 — SECA Review XLSX Workflow**

**FE-9: XLSX Upload UI**

Goal: Upload spreadsheet for automated analysis

Tasks

- File upload drop zone
- XLSX validation
- Column preview mapping
- Progress indicator

Acceptance Criteria

- Only valid XLSX accepted
- Clear upload feedback
- Errors handled gracefully

**FE-10: Download Results UI**

Goal: Deliver generated artifacts

Tasks

- Trigger backend processing
- Show processing status
- Auto-download:
    - PDF report
    - Reformatted XLSX
-
- Summary screen with counts & errors

Acceptance Criteria

- Files download automatically
- Clear success/failure messaging
- No user confusion

# **🧠 Redis + Correlation Parsing Data Schema**

This schema is designed for high-volume telemetry, horizontal scaling, and fast lookup during Selenium + trace correlation.

# **1️⃣ Primary Correlation Key (Canonical ID)**

<circuit_id>_<date>

Example:

33.L1XX.801233..TWCC_2025-12-10_01-59-32

# **2️⃣ Redis Keyspace Design**

**🔹 Circuit Event Index**

circuit:<correlation_id>

Type: HASH

{

"circuit_id": "33.L1XX.801233..TWCC",

"date": "2025-12-10_01-59-32",

"service_request_type": "ACTIVATE",

"product_name": "MDSO",

"error_message": "Unable to connect to device",

"cdnc_summary": "Connectivity check failed",

"status": "FAIL"

}

**🔹 Trace Index**

trace:<trace_id>

Type: HASH

{

"trace_id": "a91b2c...",

"service": "deviceconnectivitycheck",

"status": "FAILED",

"duration_ms": 70342,

"resource_id": "4cbd1db2-d569-11f0-b4fc-fbbc1440290a",

"correlation_id": "33.L1XX.801233..TWCC_2025-12-10_01-59-32"

}

**🔹 Log File Index**

logfile:<log_filename>

Type: HASH

{

"log_file": "plan-script-....txt",

"trace_id": "a91b2c...",

"process": "scripts.deviceconfiguration.deviceconnectivitycheck.Activate",

"state": "FAILED"

}

**🔹 Extracted Tracebacks**

traceback:<trace_id>

Type: LIST

[

"Traceback (most recent call last):",

"File \"...deviceconnectivitycheck.py\", line 58",

"Exception: Unable to connect to device at CSTNOH122ZW..."

]

**🔹 Error Grouping (for XLSX Highlighting)**

error_group:<normalized_error>

Type: SET

{

"33.L1XX.801233..TWCC_2025-12-10_01-59-32",

"44.L1YY.882190..ABC_2025-12-10_02-12-11"

}

# **3️⃣ Message Normalization Contract (OTel → Correlation Engine)**

**Normalized Event Schema**

{

"timestamp": "...",

"trace_id": "...",

"span_id": "...",

"service": "mdso",

"environment": "prod",

"level": "ERROR",

"message": "Unable to connect to device",

"exception": {

"type": "Exception",

"value": "Unable to connect...",

"stacktrace": "Traceback..."

},

"correlation_id": "..."

}

# **4️⃣ Redis Performance Strategy**

- ✅ TTL on trace/log keys (24–48h)
- ✅ Hashes for fast lookups
- ✅ Sets for grouping & deduplication
- ✅ Avoid queues for telemetry (push → parse → store)
- ✅ Redis used only as cache, not source of truth

# **5️⃣ Data Flow Summary**

Alloy (MDSO/SENSE)

→ OTel Gateway (META)

→ Correlation Engine

→ Redis (indexed + cached)

→ Selenium Analyzer

→ PDF + XLSX

Generate API contracts for frontend ↔ backend

Create Redis eviction & TTL strategy