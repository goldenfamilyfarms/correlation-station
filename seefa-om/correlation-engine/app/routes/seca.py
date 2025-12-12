"""
SECA Review API Routes
Handles XLSX upload, Selenium scraping, and report generation
Blueprint Feature 4 & 5: SECA Review Pipeline + Database Integration
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, List
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import structlog

from app.seca_xlsx_processor import SECAXLSXProcessor
from app.selenium_scraper import MDSOReportScraper
from app.pdf_generator import generate_seca_report
from app.redis_schema import RedisCorrelationStore, CircuitEvent
from app.database import create_seca_week, create_seca_error, create_seca_affected_file

logger = structlog.get_logger()

router = APIRouter(prefix="/seca", tags=["seca"])


@router.post("/upload")
async def upload_seca_xlsx(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload SECA XLSX file for processing
    
    Workflow:
    1. Parse XLSX to extract circuit errors
    2. Scrape MDSO reports using Selenium
    3. Generate PDF report
    4. Generate reformatted XLSX
    5. Return download links
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be XLSX format")

    logger.info("SECA XLSX upload started", filename=file.filename)

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        # Step 1: Parse XLSX
        processor = SECAXLSXProcessor(tmp_path)
        processor.load_xlsx()
        errors = processor.parse_circuit_data()

        logger.info("XLSX parsed", error_count=len(errors))

        # Step 2: Scrape MDSO reports
        circuit_list = [(e.circuit_id, e.date) for e in errors.values()]

        with MDSOReportScraper() as scraper:
            scraped_results = scraper.scrape_multiple_circuits(circuit_list[:10])  # Limit to 10 for demo

        logger.info("Selenium scraping complete", scraped_count=len(scraped_results))

        # Merge scraped data into errors
        for concat_key, scraped in scraped_results.items():
            if concat_key in errors:
                errors[concat_key].traceback = scraped.traceback
                errors[concat_key].log_file_path = scraped.log_file
                errors[concat_key].categorized_error = scraped.categorized_error
                errors[concat_key].affected_files = scraped.affected_files

        # Step 3: Group errors by type
        error_groups: Dict[str, List[str]] = {}
        for concat_key, error in errors.items():
            error_type = error.categorized_error or "Unknown"
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error.circuit_id)

        # Step 4: Generate PDF report
        pdf_path = tempfile.mktemp(suffix='.pdf')
        generate_seca_report(
            output_path=pdf_path,
            errors=processor.to_dict(),
            error_groups=error_groups
        )

        logger.info("PDF report generated", path=pdf_path)

        # Step 5: Generate reformatted XLSX
        xlsx_path = tempfile.mktemp(suffix='.xlsx')
        processor.generate_reformatted_xlsx(xlsx_path)

        logger.info("Reformatted XLSX generated", path=xlsx_path)

        # Step 6: Save to database (Blueprint Feature 5)
        # Create SECA week entry
        week_id = str(uuid.uuid4())
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
        
        # Count circuits with traceback
        circuits_with_traceback = sum(1 for e in errors.values() if e.traceback or (e.affected_files and any(af.traceback for af in e.affected_files)))
        
        summary_text = f"SECA Review for week {week_start} to {week_end}. Total circuits: {len(errors)}, Circuits with traceback: {circuits_with_traceback}"
        
        await create_seca_week(
            week_id=week_id,
            week_start_date=week_start,
            week_end_date=week_end,
            summary_text=summary_text,
            total_circuits=len(errors),
            circuits_with_traceback=circuits_with_traceback
        )
        
        # Save each error to database
        saved_error_ids = []
        for concat_key, error in errors.items():
            error_id = str(uuid.uuid4())
            
            # Determine primary traceback (from error or first affected file)
            primary_traceback = error.traceback
            if not primary_traceback and error.affected_files:
                for af in error.affected_files:
                    if af.traceback:
                        primary_traceback = af.traceback
                        break
            
            await create_seca_error(
                error_id=error_id,
                seca_week_id=week_id,
                circuit_id=error.circuit_id,
                date=error.date,
                service_request_type=error.service_request_type,
                product_name=error.product_name,
                error_message=error.error_message,
                cdnc_summary=error.cdnc_summary,
                fallout_reason=error.categorized_error,
                priority="medium",  # Could be determined from error type
                application=None,  # Could be determined from product_name
                status="new",
                meta_web_link=f"http://159.56.4.94/reports",  # Meta Web Tool base URL
                analysis_pdf_url=pdf_path if os.path.exists(pdf_path) else None,
                traceback=primary_traceback
            )
            
            # Save affected files
            for af in error.affected_files:
                file_id = str(uuid.uuid4())
                await create_seca_affected_file(
                    file_id=file_id,
                    seca_error_id=error_id,
                    source=af.source,
                    log_file=af.log_file,
                    traceback=af.traceback,
                    artifact_url=af.artifact_url,
                    selenium_status=af.selenium_status
                )
            
            saved_error_ids.append(error_id)
        
        logger.info("SECA data saved to database", week_id=week_id, error_count=len(saved_error_ids))

        # Return file paths for download
        return {
            "status": "success",
            "total_errors": len(errors),
            "scraped_errors": len(scraped_results),
            "error_groups": len(error_groups),
            "seca_week_id": week_id,
            "pdf_report": pdf_path,
            "reformatted_xlsx": xlsx_path,
            "download_urls": {
                "pdf": f"/seca/download/pdf?path={pdf_path}",
                "xlsx": f"/seca/download/xlsx?path={xlsx_path}"
            }
        }

    except Exception as e:
        logger.error("SECA processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    finally:
        # Cleanup uploaded file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/download/pdf")
async def download_pdf(path: str):
    """Download generated PDF report"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=path,
        media_type='application/pdf',
        filename='seca_report.pdf'
    )


@router.get("/download/xlsx")
async def download_xlsx(path: str):
    """Download reformatted XLSX"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="XLSX not found")

    return FileResponse(
        path=path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename='seca_reformatted.xlsx'
    )


@router.post("/store-redis")
async def store_in_redis(errors: Dict[str, Dict]):
    """
    Store circuit errors in Redis for correlation
    
    This endpoint is called after XLSX processing to cache errors
    """
    try:
        # Initialize Redis store (assumes Redis client is configured)
        from app.dependencies import get_redis_client
        redis_client = get_redis_client()
        store = RedisCorrelationStore(redis_client)

        stored_count = 0
        for concat_key, error_data in errors.items():
            # Create CircuitEvent
            event = CircuitEvent(
                circuit_id=error_data['circuit_id'],
                date=error_data['date'],
                service_request_type=error_data['service_request_type'],
                product_name=error_data['product_name'],
                error_message=error_data['error_message'],
                cdnc_summary=error_data['initial_cdnc_summary'],
                status='FAIL'
            )

            # Store in Redis
            correlation_id = store.store_circuit_event(event)

            # Store traceback if available
            if error_data.get('traceback'):
                traceback_lines = error_data['traceback'].split('\n')
                store.store_traceback(correlation_id, traceback_lines)

            # Add to error group
            if error_data.get('categorized_error'):
                normalized = store.normalize_error(error_data['error_message'])
                store.add_to_error_group(normalized, correlation_id)

            stored_count += 1

        logger.info("Errors stored in Redis", count=stored_count)

        return {
            "status": "success",
            "stored_count": stored_count
        }

    except Exception as e:
        logger.error("Redis storage failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Redis storage failed: {str(e)}")
