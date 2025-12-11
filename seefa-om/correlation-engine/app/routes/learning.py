"""
Learning modules and progress tracking API endpoints
Blueprint Feature 5: Backend + Database for Correlation Station
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import aiosqlite
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/learning", tags=["learning"])


# ===== MODELS =====

class LearningModule(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str]
    display_order: int
    created_at: str
    updated_at: str


class LearningLesson(BaseModel):
    id: str
    module_id: str
    title: str
    video_url: Optional[str]
    content_md: Optional[str]
    display_order: int
    created_at: str
    updated_at: str


class UserLessonProgress(BaseModel):
    id: str
    user_id: str
    lesson_id: str
    status: str  # not_started, in_progress, completed
    last_viewed_at: Optional[str]
    completed_at: Optional[str]


class ProgressUpdate(BaseModel):
    lesson_id: str
    status: str  # in_progress, completed


class ModuleWithLessons(BaseModel):
    module: LearningModule
    lessons: List[LearningLesson]
    progress: Optional[dict]  # lesson_id -> status


# ===== DEPENDENCIES =====

async def get_db():
    """Get database connection"""
    db = await aiosqlite.connect("correlation_station.db")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def get_current_user_id():
    """Get current user ID from auth token

    TODO: Implement proper auth middleware
    For now, return a test user
    """
    return "test_user_123"


# ===== ENDPOINTS =====

@router.get("/modules", response_model=List[LearningModule])
async def get_learning_modules(db: aiosqlite.Connection = Depends(get_db)):
    """
    Get all learning modules

    Returns list of modules ordered by display_order
    """
    try:
        async with db.execute(
            "SELECT * FROM learning_modules ORDER BY display_order ASC"
        ) as cursor:
            rows = await cursor.fetchall()

        modules = [
            LearningModule(
                id=row["id"],
                slug=row["slug"],
                title=row["title"],
                description=row["description"],
                display_order=row["display_order"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

        logger.info("Fetched learning modules", count=len(modules))
        return modules

    except Exception as e:
        logger.error("Error fetching learning modules", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch learning modules")


@router.get("/modules/{module_id}", response_model=ModuleWithLessons)
async def get_learning_module(
    module_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get a specific learning module with its lessons and user progress

    Returns:
        - Module details
        - List of lessons
        - User progress for each lesson
    """
    try:
        # Get module
        async with db.execute(
            "SELECT * FROM learning_modules WHERE id = ? OR slug = ?",
            (module_id, module_id)
        ) as cursor:
            module_row = await cursor.fetchone()

        if not module_row:
            raise HTTPException(status_code=404, detail="Module not found")

        module = LearningModule(
            id=module_row["id"],
            slug=module_row["slug"],
            title=module_row["title"],
            description=module_row["description"],
            display_order=module_row["display_order"],
            created_at=module_row["created_at"],
            updated_at=module_row["updated_at"]
        )

        # Get lessons
        async with db.execute(
            "SELECT * FROM learning_lessons WHERE module_id = ? ORDER BY display_order ASC",
            (module.id,)
        ) as cursor:
            lesson_rows = await cursor.fetchall()

        lessons = [
            LearningLesson(
                id=row["id"],
                module_id=row["module_id"],
                title=row["title"],
                video_url=row["video_url"],
                content_md=row["content_md"],
                display_order=row["display_order"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in lesson_rows
        ]

        # Get user progress
        lesson_ids = [lesson.id for lesson in lessons]
        progress = {}

        if lesson_ids:
            placeholders = ",".join("?" * len(lesson_ids))
            async with db.execute(
                f"SELECT lesson_id, status FROM user_lesson_progress WHERE user_id = ? AND lesson_id IN ({placeholders})",
                (user_id, *lesson_ids)
            ) as cursor:
                progress_rows = await cursor.fetchall()

            progress = {
                row["lesson_id"]: row["status"]
                for row in progress_rows
            }

        logger.info(
            "Fetched module with lessons",
            module_id=module.id,
            lesson_count=len(lessons),
            progress_count=len(progress)
        )

        return ModuleWithLessons(
            module=module,
            lessons=lessons,
            progress=progress
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching module", module_id=module_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch module")


@router.get("/progress", response_model=List[UserLessonProgress])
async def get_user_progress(
    db: aiosqlite.Connection = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all progress for current user

    Returns list of user lesson progress records
    """
    try:
        async with db.execute(
            "SELECT * FROM user_lesson_progress WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        progress = [
            UserLessonProgress(
                id=row["id"],
                user_id=row["user_id"],
                lesson_id=row["lesson_id"],
                status=row["status"],
                last_viewed_at=row["last_viewed_at"],
                completed_at=row["completed_at"]
            )
            for row in rows
        ]

        logger.info("Fetched user progress", user_id=user_id, count=len(progress))
        return progress

    except Exception as e:
        logger.error("Error fetching user progress", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch progress")


@router.post("/progress")
async def update_progress(
    progress_update: ProgressUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Update user progress for a lesson

    Args:
        progress_update: Lesson ID and new status

    Returns:
        Updated progress record
    """
    try:
        # Validate lesson exists
        async with db.execute(
            "SELECT id FROM learning_lessons WHERE id = ?",
            (progress_update.lesson_id,)
        ) as cursor:
            lesson = await cursor.fetchone()

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Check if progress record exists
        async with db.execute(
            "SELECT id FROM user_lesson_progress WHERE user_id = ? AND lesson_id = ?",
            (user_id, progress_update.lesson_id)
        ) as cursor:
            existing = await cursor.fetchone()

        now = datetime.utcnow().isoformat()

        if existing:
            # Update existing
            await db.execute(
                """
                UPDATE user_lesson_progress
                SET status = ?,
                    last_viewed_at = ?,
                    completed_at = CASE WHEN ? = 'completed' THEN ? ELSE completed_at END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    progress_update.status,
                    now,
                    progress_update.status,
                    now,
                    now,
                    existing["id"]
                )
            )
            progress_id = existing["id"]
        else:
            # Create new
            progress_id = str(uuid.uuid4())
            completed_at = now if progress_update.status == "completed" else None

            await db.execute(
                """
                INSERT INTO user_lesson_progress
                (id, user_id, lesson_id, status, last_viewed_at, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    progress_id,
                    user_id,
                    progress_update.lesson_id,
                    progress_update.status,
                    now,
                    completed_at,
                    now,
                    now
                )
            )

        await db.commit()

        # Fetch updated record
        async with db.execute(
            "SELECT * FROM user_lesson_progress WHERE id = ?",
            (progress_id,)
        ) as cursor:
            row = await cursor.fetchone()

        logger.info(
            "Updated lesson progress",
            user_id=user_id,
            lesson_id=progress_update.lesson_id,
            status=progress_update.status
        )

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "lesson_id": row["lesson_id"],
            "status": row["status"],
            "last_viewed_at": row["last_viewed_at"],
            "completed_at": row["completed_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating progress", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update progress")


@router.get("/stats")
async def get_progress_stats(
    db: aiosqlite.Connection = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get progress statistics for current user

    Returns:
        - Total lessons
        - Completed lessons
        - In-progress lessons
        - Completion percentage
    """
    try:
        # Total lessons
        async with db.execute("SELECT COUNT(*) as total FROM learning_lessons") as cursor:
            total_row = await cursor.fetchone()
            total_lessons = total_row["total"]

        # User progress counts
        async with db.execute(
            """
            SELECT status, COUNT(*) as count
            FROM user_lesson_progress
            WHERE user_id = ?
            GROUP BY status
            """,
            (user_id,)
        ) as cursor:
            progress_rows = await cursor.fetchall()

        progress_counts = {row["status"]: row["count"] for row in progress_rows}

        completed = progress_counts.get("completed", 0)
        in_progress = progress_counts.get("in_progress", 0)
        not_started = total_lessons - (completed + in_progress)

        completion_percentage = (completed / total_lessons * 100) if total_lessons > 0 else 0

        stats = {
            "total_lessons": total_lessons,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_percentage": round(completion_percentage, 1)
        }

        logger.info("Fetched progress stats", user_id=user_id, stats=stats)
        return stats

    except Exception as e:
        logger.error("Error fetching stats", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
