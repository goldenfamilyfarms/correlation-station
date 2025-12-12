"""
SQLite database for SECA error reviews
"""
import aiosqlite
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()

DATABASE_PATH = Path("/app/data/seca_reviews.db")


async def init_database():
    """Initialize the SQLite database with required tables
    
    Blueprint Feature 5: Initializes full database schema from database_schema.sql
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read and execute the full schema SQL file
    schema_file = Path(__file__).parent / "database_schema.sql"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if schema_file.exists():
            # Execute full schema from SQL file
            schema_sql = schema_file.read_text()
            await db.executescript(schema_sql)
            logger.info("Database schema initialized from database_schema.sql", path=str(DATABASE_PATH))
        else:
            # Fallback to legacy schema if SQL file doesn't exist
            logger.warning("database_schema.sql not found, using legacy schema")
            
            # SECA Error Reviews table (legacy)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS error_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT NOT NULL,
                    errors TEXT NOT NULL
                )
            """)

            # Users table for authentication (legacy - will be upgraded by schema.sql)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tutorial progress table (legacy)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tutorial_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    tutorial_id TEXT NOT NULL,
                    completed BOOLEAN DEFAULT 0,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE (user_id, tutorial_id)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tutorial_progress_user
                ON tutorial_progress (user_id)
            """)

        await db.commit()
        logger.info("Database initialized", path=str(DATABASE_PATH))


async def get_all_reviews() -> List[Dict[str, Any]]:
    """Get all error reviews"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM error_reviews ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "period": row["period"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "summary": row["summary"],
                    "errors": json.loads(row["errors"]),
                }
                for row in rows
            ]


async def get_review_by_id(review_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific error review by ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM error_reviews WHERE id = ?", (review_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "period": row["period"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "summary": row["summary"],
                    "errors": json.loads(row["errors"]),
                }
            return None


async def create_review(
    period: str, summary: str, errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a new error review"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO error_reviews (period, summary, errors)
            VALUES (?, ?, ?)
            """,
            (period, summary, json.dumps(errors)),
        )
        await db.commit()
        review_id = cursor.lastrowid
        return await get_review_by_id(review_id)


async def update_review(
    review_id: int, summary: str, errors: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Update an existing error review"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if errors is not None:
            await db.execute(
                """
                UPDATE error_reviews
                SET summary = ?, errors = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (summary, json.dumps(errors), review_id),
            )
        else:
            await db.execute(
                """
                UPDATE error_reviews
                SET summary = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (summary, review_id),
            )
        await db.commit()
        return await get_review_by_id(review_id)


async def delete_review(review_id: int) -> bool:
    """Delete an error review"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM error_reviews WHERE id = ?", (review_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def seed_sample_data():
    """Seed database with sample SECA review data"""
    # Check if we already have data
    reviews = await get_all_reviews()
    if reviews:
        return

    sample_reviews = [
        {
            "period": "Week 46 - Nov 11-15, 2024",
            "summary": """This week we observed a 23% reduction in critical errors compared to last week.

The primary focus was on resolving authentication timeout issues and database connection pool exhaustion in the payment service.

Key Achievements:
- Implemented connection pooling improvements in payment-service (reduced connection errors by 67%)
- Fixed race condition in auth-service token refresh (eliminated 95% of auth timeouts)
- Deployed circuit breaker pattern for external API calls (improved resilience)

Ongoing Concerns:
- API gateway still experiencing intermittent 502 errors during traffic spikes
- Need to investigate memory leak in notification-service (gradual OOM errors)""",
            "errors": [
                {
                    "id": "ERR-2024-11-001",
                    "service": "payment-service",
                    "error_type": "Database Connection Pool Exhaustion",
                    "count": 2847,
                    "severity": "critical",
                    "description": "Payment service exhausting database connection pool during peak hours, causing transaction failures",
                    "root_cause": "Connection pool size too small (10 connections) for peak load. Connections not being properly released after transactions.",
                    "resolution_status": "resolved",
                    "action_items": [
                        "Increased pool size from 10 to 50 connections",
                        "Implemented connection timeout of 30 seconds",
                        "Added connection leak detection logging",
                        "Set up alerts for pool utilization > 80%"
                    ],
                    "responsible_team": "Platform Team"
                },
                {
                    "id": "ERR-2024-11-002",
                    "service": "auth-service",
                    "error_type": "Token Refresh Race Condition",
                    "count": 1234,
                    "severity": "high",
                    "description": "Multiple concurrent token refresh requests causing race condition and authentication failures",
                    "root_cause": "Token refresh logic not thread-safe. Multiple threads attempting to refresh same token simultaneously.",
                    "resolution_status": "resolved",
                    "action_items": [
                        "Implemented distributed lock using Redis",
                        "Added token refresh queue with deduplication",
                        "Increased token TTL from 15min to 30min",
                        "Added metrics for token refresh failures"
                    ],
                    "responsible_team": "Auth Team"
                },
                {
                    "id": "ERR-2024-11-003",
                    "service": "api-gateway",
                    "error_type": "502 Bad Gateway During Traffic Spikes",
                    "count": 456,
                    "severity": "high",
                    "description": "API gateway returning 502 errors during sudden traffic increases",
                    "root_cause": "Upstream services not scaling fast enough. Gateway timeout set too low (5s).",
                    "resolution_status": "in_progress",
                    "action_items": [
                        "Increase gateway timeout to 30s",
                        "Implement predictive autoscaling based on traffic patterns",
                        "Add request queuing with backpressure",
                        "Configure circuit breaker for upstream services"
                    ],
                    "responsible_team": "Infrastructure Team"
                },
                {
                    "id": "ERR-2024-11-004",
                    "service": "notification-service",
                    "error_type": "Gradual Memory Leak (OOM)",
                    "count": 12,
                    "severity": "medium",
                    "description": "Notification service experiencing gradual memory growth leading to OOM crashes every 48 hours",
                    "root_cause": "Under investigation. Suspected WebSocket connection leak or message queue buffer growth.",
                    "resolution_status": "investigating",
                    "action_items": [
                        "Enable heap dump on OOM",
                        "Add memory profiling with Pyroscope",
                        "Investigate WebSocket connection lifecycle",
                        "Review message queue buffer configuration"
                    ],
                    "responsible_team": "Backend Team"
                }
            ]
        }
    ]

    for review_data in sample_reviews:
        await create_review(
            period=review_data["period"],
            summary=review_data["summary"],
            errors=review_data["errors"]
        )

    logger.info("Sample SECA review data seeded")


# ====================
# USER MANAGEMENT
# ====================

async def create_user(user_id: str, username: str, email: str, password_hash: str) -> Dict[str, Any]:
    """Create a new user"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                """
                INSERT INTO users (id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, email, password_hash),
            )
            await db.commit()
            return await get_user_by_id(user_id)
        except aiosqlite.IntegrityError as e:
            logger.error("Failed to create user", error=str(e))
            raise ValueError("Username or email already exists")


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                }
            return None


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username (includes password_hash for auth)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "created_at": row["created_at"],
                }
            return None


# ====================
# TUTORIAL PROGRESS
# ====================

async def mark_tutorial_complete(user_id: str, tutorial_id: str) -> bool:
    """Mark a tutorial as complete for a user"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO tutorial_progress (user_id, tutorial_id, completed, completed_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (user_id, tutorial_id),
        )
        await db.commit()
        return True


async def get_user_progress(user_id: str) -> List[Dict[str, Any]]:
    """Get all tutorial progress for a user"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT tutorial_id, completed, completed_at
            FROM tutorial_progress
            WHERE user_id = ? AND completed = 1
            """,
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "tutorial_id": row["tutorial_id"],
                    "completed": bool(row["completed"]),
                    "completed_at": row["completed_at"],
                }
                for row in rows
            ]


async def is_tutorial_complete(user_id: str, tutorial_id: str) -> bool:
    """Check if a specific tutorial is complete"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """
            SELECT completed FROM tutorial_progress
            WHERE user_id = ? AND tutorial_id = ?
            """,
            (user_id, tutorial_id),
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False


# ====================
# SECA WEEKS & ERRORS
# Blueprint Feature 5: Database functions for SECA data
# ====================

async def create_seca_week(
    week_id: str,
    week_start_date: str,
    week_end_date: str,
    summary_text: Optional[str] = None,
    total_circuits: int = 0,
    circuits_with_traceback: int = 0
) -> Dict[str, Any]:
    """Create a new SECA week"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO seca_weeks 
            (id, week_start_date, week_end_date, summary_text, total_circuits, circuits_with_traceback)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (week_id, week_start_date, week_end_date, summary_text, total_circuits, circuits_with_traceback)
        )
        await db.commit()
        
        async with db.execute(
            "SELECT * FROM seca_weeks WHERE id = ?",
            (week_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def create_seca_error(
    error_id: str,
    seca_week_id: str,
    circuit_id: str,
    date: str,
    service_request_type: Optional[str] = None,
    product_name: Optional[str] = None,
    error_message: Optional[str] = None,
    cdnc_summary: Optional[str] = None,
    fallout_reason: Optional[str] = None,
    priority: str = "medium",
    application: Optional[str] = None,
    team: Optional[str] = None,
    owner: Optional[str] = None,
    status: str = "new",
    grafana_link: Optional[str] = None,
    meta_web_link: Optional[str] = None,
    analysis_pdf_url: Optional[str] = None,
    traceback: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new SECA error"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT OR REPLACE INTO seca_errors
            (id, seca_week_id, circuit_id, date, service_request_type, product_name,
             error_message, cdnc_summary, fallout_reason, priority, application,
             team, owner, status, grafana_link, meta_web_link, analysis_pdf_url, traceback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (error_id, seca_week_id, circuit_id, date, service_request_type, product_name,
             error_message, cdnc_summary, fallout_reason, priority, application,
             team, owner, status, grafana_link, meta_web_link, analysis_pdf_url, traceback)
        )
        await db.commit()
        
        async with db.execute(
            "SELECT * FROM seca_errors WHERE id = ?",
            (error_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def create_seca_affected_file(
    file_id: str,
    seca_error_id: str,
    source: str,
    log_file: Optional[str] = None,
    traceback: Optional[str] = None,
    artifact_url: Optional[str] = None,
    selenium_status: str = "ok"
) -> Dict[str, Any]:
    """Create a new SECA affected file"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO seca_affected_files
            (id, seca_error_id, source, log_file, traceback, artifact_url, selenium_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (file_id, seca_error_id, source, log_file, traceback, artifact_url, selenium_status)
        )
        await db.commit()
        
        async with db.execute(
            "SELECT * FROM seca_affected_files WHERE id = ?",
            (file_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}