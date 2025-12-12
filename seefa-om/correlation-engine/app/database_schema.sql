-- Database Schema for Correlation Station
-- Blueprint Feature 5: Backend + Database for Correlation Station
-- SQLite schema with tables for users, learning, SECA, and documentation

-- ===== USERS TABLE (already exists, enhanced) =====
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'dev',  -- dev, SRE, manager, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ===== LEARNING MODULES & PROGRESS =====

-- Learning modules (e.g., Grafana 101, MDSO Overview, OTel Instrumentation)
CREATE TABLE IF NOT EXISTS learning_modules (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,  -- grafana-101, mdso-overview
    title TEXT NOT NULL,
    description TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learning_modules_slug ON learning_modules(slug);
CREATE INDEX IF NOT EXISTS idx_learning_modules_order ON learning_modules(display_order);

-- Learning lessons within modules
CREATE TABLE IF NOT EXISTS learning_lessons (
    id TEXT PRIMARY KEY,
    module_id TEXT NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT,
    content_md TEXT,  -- Markdown content
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES learning_modules(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_learning_lessons_module ON learning_lessons(module_id);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_order ON learning_lessons(display_order);

-- User progress tracking for lessons
CREATE TABLE IF NOT EXISTS user_lesson_progress (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started',  -- not_started, in_progress, completed
    last_viewed_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES learning_lessons(id) ON DELETE CASCADE,
    UNIQUE(user_id, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_user_lesson_progress_user ON user_lesson_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_lesson_progress_lesson ON user_lesson_progress(lesson_id);

-- ===== SECA WEEKS & ERRORS =====

-- SECA weekly review summaries
CREATE TABLE IF NOT EXISTS seca_weeks (
    id TEXT PRIMARY KEY,
    week_start_date TEXT NOT NULL,  -- YYYY-MM-DD format
    week_end_date TEXT NOT NULL,    -- YYYY-MM-DD format
    summary_text TEXT,              -- Executive summary of week's SECA review
    total_circuits INTEGER DEFAULT 0,
    circuits_with_traceback INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_seca_weeks_start ON seca_weeks(week_start_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_seca_weeks_dates ON seca_weeks(week_start_date, week_end_date);

-- SECA error details (Blueprint 4.4 structured format)
CREATE TABLE IF NOT EXISTS seca_errors (
    id TEXT PRIMARY KEY,
    seca_week_id TEXT NOT NULL,
    circuit_id TEXT NOT NULL,
    date TEXT NOT NULL,  -- Circuit failure date
    service_request_type TEXT,
    product_name TEXT,
    error_message TEXT,
    cdnc_summary TEXT,
    fallout_reason TEXT,  -- Categorized error (MDSO | Device Connectivity, etc.)
    priority TEXT DEFAULT 'medium',  -- low, medium, high, critical
    application TEXT,  -- Sense, MDSO, IP Control, Kong, Granite
    team TEXT,         -- Responsible team
    owner TEXT,        -- Assigned owner
    status TEXT DEFAULT 'new',  -- new, triage, in_progress, resolved, closed
    grafana_link TEXT,  -- Link to Grafana dashboard
    meta_web_link TEXT, -- Link to Meta Web Tool report
    analysis_pdf_url TEXT,  -- Link to generated PDF report
    traceback TEXT,     -- Full traceback
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seca_week_id) REFERENCES seca_weeks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_seca_errors_week ON seca_errors(seca_week_id);
CREATE INDEX IF NOT EXISTS idx_seca_errors_circuit ON seca_errors(circuit_id);
CREATE INDEX IF NOT EXISTS idx_seca_errors_status ON seca_errors(status);
CREATE INDEX IF NOT EXISTS idx_seca_errors_application ON seca_errors(application);
CREATE UNIQUE INDEX IF NOT EXISTS idx_seca_errors_circuit_date ON seca_errors(circuit_id, date);

-- SECA affected files (many-to-one with seca_errors)
CREATE TABLE IF NOT EXISTS seca_affected_files (
    id TEXT PRIMARY KEY,
    seca_error_id TEXT NOT NULL,
    source TEXT NOT NULL,  -- orch_trace, other_log
    log_file TEXT,
    traceback TEXT,
    artifact_url TEXT,
    selenium_status TEXT,  -- ok, artifact_not_found, traceback_not_found, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seca_error_id) REFERENCES seca_errors(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_seca_affected_files_error ON seca_affected_files(seca_error_id);

-- ===== DOCUMENTATION PAGES =====

-- Documentation content pages
CREATE TABLE IF NOT EXISTS docs_pages (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,  -- overview, architecture, otel-instrumentation
    title TEXT NOT NULL,
    section TEXT,  -- overview, architecture, development, operations
    content_md TEXT NOT NULL,  -- Markdown content
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_pages_slug ON docs_pages(slug);
CREATE INDEX IF NOT EXISTS idx_docs_pages_section ON docs_pages(section);
CREATE INDEX IF NOT EXISTS idx_docs_pages_order ON docs_pages(display_order);

-- ===== SAMPLE DATA SEEDS =====

-- Sample learning module
INSERT OR IGNORE INTO learning_modules (id, slug, title, description, display_order) VALUES
    ('module_grafana_101', 'grafana-101', 'Grafana 101', 'Introduction to Grafana dashboards and queries', 1),
    ('module_mdso_overview', 'mdso-overview', 'MDSO Overview', 'Understanding Multi-Domain Service Orchestrator', 2),
    ('module_otel', 'otel-instrumentation', 'OpenTelemetry Instrumentation', 'Learn how to instrument applications with OTel', 3);

-- Sample lessons for Grafana 101
INSERT OR IGNORE INTO learning_lessons (id, module_id, title, video_url, content_md, display_order) VALUES
    ('lesson_grafana_basics', 'module_grafana_101', 'Grafana Basics', 'https://youtube.com/watch?v=example1', '# Grafana Basics\n\nLearn the fundamentals of Grafana.', 1),
    ('lesson_logql', 'module_grafana_101', 'LogQL Queries', 'https://youtube.com/watch?v=example2', '# LogQL Queries\n\nMaster LogQL for Loki log queries.', 2);

-- Sample documentation pages
INSERT OR IGNORE INTO docs_pages (id, slug, title, section, content_md, display_order) VALUES
    ('doc_overview', 'overview', 'Correlation Station Overview', 'overview', '# Overview\n\nWelcome to Correlation Station.', 1),
    ('doc_architecture', 'architecture', 'System Architecture', 'architecture', '# Architecture\n\nDetailed architecture documentation.', 2),
    ('doc_otel', 'otel-instrumentation', 'OTel Instrumentation Guide', 'development', '# OpenTelemetry\n\nHow to instrument your services.', 3);
