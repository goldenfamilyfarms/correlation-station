"""
SECA Weeks and Errors API endpoints
Blueprint Feature 5: Backend + Database for Correlation Station
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import aiosqlite
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/seca", tags=["seca-data"])

# ===== MODELS =====

class SECAWeek(BaseModel):
    id: str
    week_start_date: str
    week_end_date: str
    summary_text: Optional[str]
    total_circuits: int
    circuits_with_traceback: int
    created_at: str
    updated_at: str


class SECAError(BaseModel):
    id: str
    seca_week_id: str
    circuit_id: str
    date: str
    service_request_type: Optional[str]
    product_name: Optional[str]
    error_message: Optional[str]
    cdnc_summary: Optional[str]
    fallout_reason: Optional[str]
    priority: str
    application: Optional[str]
    team: Optional[str]
    owner: Optional[str]
    status: str
    grafana_link: Optional[str]
    meta_web_link: Optional[str]
    analysis_pdf_url: Optional[str]
    traceback: Optional[str]
    created_at: str
    updated_at: str


class AffectedFile(BaseModel):
    id: str
    seca_error_id: str
    source: str
    log_file: Optional[str]
    traceback: Optional[str]
    artifact_url: Optional[str]
    selenium_status: str
    created_at: str


class SECAErrorWithFiles(SECAError):
    affected_files: List[AffectedFile] = []


# ===== DEPENDENCIES =====

async def get_db():
    """Get database connection"""
    from app.database import DATABASE_PATH
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


# ===== ENDPOINTS =====

@router.get("/weeks", response_model=List[SECAWeek])
async def get_seca_weeks(
    db: aiosqlite.Connection = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0)
):
    """
    Get all SECA weeks
    
    Returns list of weekly SECA review summaries ordered by week_start_date DESC
    """
    try:
        async with db.execute(
            """
            SELECT * FROM seca_weeks 
            ORDER BY week_start_date DESC 
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()

        weeks = [
            SECAWeek(
                id=row["id"],
                week_start_date=row["week_start_date"],
                week_end_date=row["week_end_date"],
                summary_text=row["summary_text"],
                total_circuits=row["total_circuits"],
                circuits_with_traceback=row["circuits_with_traceback"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

        logger.info("Fetched SECA weeks", count=len(weeks))
        return weeks

    except Exception as e:
        logger.error("Error fetching SECA weeks", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch SECA weeks")


@router.get("/weeks/{week_id}", response_model=SECAWeek)
async def get_seca_week(
    week_id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Get a specific SECA week by ID
    """
    try:
        async with db.execute(
            "SELECT * FROM seca_weeks WHERE id = ?",
            (week_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="SECA week not found")

        return SECAWeek(
            id=row["id"],
            week_start_date=row["week_start_date"],
            week_end_date=row["week_end_date"],
            summary_text=row["summary_text"],
            total_circuits=row["total_circuits"],
            circuits_with_traceback=row["circuits_with_traceback"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching SECA week", week_id=week_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch SECA week")


@router.get("/errors", response_model=List[SECAError])
async def get_seca_errors(
    db: aiosqlite.Connection = Depends(get_db),
    week_id: Optional[str] = Query(None, description="Filter by SECA week ID"),
    circuit_id: Optional[str] = Query(None, description="Filter by circuit ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    application: Optional[str] = Query(None, description="Filter by application"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """
    Get SECA errors with optional filters
    
    Filters:
    - week_id: Filter by SECA week
    - circuit_id: Filter by circuit ID
    - status: Filter by status (new, triage, in_progress, resolved, closed)
    - application: Filter by application (Sense, MDSO, IP Control, etc.)
    """
    try:
        query = "SELECT * FROM seca_errors WHERE 1=1"
        params = []

        if week_id:
            query += " AND seca_week_id = ?"
            params.append(week_id)
        if circuit_id:
            query += " AND circuit_id = ?"
            params.append(circuit_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        if application:
            query += " AND application = ?"
            params.append(application)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        errors = [
            SECAError(
                id=row["id"],
                seca_week_id=row["seca_week_id"],
                circuit_id=row["circuit_id"],
                date=row["date"],
                service_request_type=row["service_request_type"],
                product_name=row["product_name"],
                error_message=row["error_message"],
                cdnc_summary=row["cdnc_summary"],
                fallout_reason=row["fallout_reason"],
                priority=row["priority"],
                application=row["application"],
                team=row["team"],
                owner=row["owner"],
                status=row["status"],
                grafana_link=row["grafana_link"],
                meta_web_link=row["meta_web_link"],
                analysis_pdf_url=row["analysis_pdf_url"],
                traceback=row["traceback"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

        logger.info("Fetched SECA errors", count=len(errors), filters={
            "week_id": week_id,
            "circuit_id": circuit_id,
            "status": status,
            "application": application
        })
        return errors

    except Exception as e:
        logger.error("Error fetching SECA errors", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch SECA errors")


@router.get("/errors/{error_id}", response_model=SECAErrorWithFiles)
async def get_seca_error(
    error_id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Get a specific SECA error by ID with affected files
    """
    try:
        # Get error
        async with db.execute(
            "SELECT * FROM seca_errors WHERE id = ?",
            (error_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="SECA error not found")

        # Get affected files
        async with db.execute(
            "SELECT * FROM seca_affected_files WHERE seca_error_id = ?",
            (error_id,)
        ) as cursor:
            file_rows = await cursor.fetchall()

        affected_files = [
            AffectedFile(
                id=file_row["id"],
                seca_error_id=file_row["seca_error_id"],
                source=file_row["source"],
                log_file=file_row["log_file"],
                traceback=file_row["traceback"],
                artifact_url=file_row["artifact_url"],
                selenium_status=file_row["selenium_status"],
                created_at=file_row["created_at"]
            )
            for file_row in file_rows
        ]

        error = SECAErrorWithFiles(
            id=row["id"],
            seca_week_id=row["seca_week_id"],
            circuit_id=row["circuit_id"],
            date=row["date"],
            service_request_type=row["service_request_type"],
            product_name=row["product_name"],
            error_message=row["error_message"],
            cdnc_summary=row["cdnc_summary"],
            fallout_reason=row["fallout_reason"],
            priority=row["priority"],
            application=row["application"],
            team=row["team"],
            owner=row["owner"],
            status=row["status"],
            grafana_link=row["grafana_link"],
            meta_web_link=row["meta_web_link"],
            analysis_pdf_url=row["analysis_pdf_url"],
            traceback=row["traceback"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            affected_files=affected_files
        )

        logger.info("Fetched SECA error", error_id=error_id, affected_files_count=len(affected_files))
        return error

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching SECA error", error_id=error_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch SECA error")

