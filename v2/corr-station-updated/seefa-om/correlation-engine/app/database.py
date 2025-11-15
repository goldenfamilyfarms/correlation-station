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
    """Initialize the SQLite database with required tables"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
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


async def update_review(review_id: int, summary: str) -> Optional[Dict[str, Any]]:
    """Update an existing error review"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
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
