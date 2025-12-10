"""
File upload and processing for SECA reviews
"""
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import structlog
import io
import re
import tempfile
import zipfile
import asyncio
import os
import uuid
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Tuple
from rq import Queue as RQQueue
from redis import Redis

logger = structlog.get_logger()

router = APIRouter()


async def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        # Try importing PyPDF2
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except ImportError:
            # Fallback: return a message indicating PDF parsing is not available
            logger.warning("PyPDF2 not installed, cannot parse PDF")
            return "PDF parsing not available. Please install PyPDF2."
    except Exception as e:
        logger.exception("Failed to extract PDF text", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")


async def extract_text_from_markdown(file_content: bytes) -> str:
    """Extract text from Markdown file"""
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        logger.exception("Failed to decode markdown", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to parse markdown: {str(e)}")


async def generate_summary(text: str) -> str:
    """Generate executive summary from text

    In a production environment, this would call an AI service like Claude API
    For now, we'll create a basic summary by extracting key information
    """
    # Simple extractive summary - take first few sentences
    sentences = re.split(r'[.!?]+', text)
    summary_sentences = []

    # Look for sentences with keywords
    keywords = ['error', 'issue', 'problem', 'resolved', 'fixed', 'critical', 'high', 'medium', 'low']

    for sentence in sentences[:50]:  # Check first 50 sentences
        if any(keyword in sentence.lower() for keyword in keywords):
            summary_sentences.append(sentence.strip())
            if len(summary_sentences) >= 10:
                break

    if not summary_sentences:
        # Fallback: take first 5 sentences
        summary_sentences = [s.strip() for s in sentences[:5] if s.strip()]

    return '\n'.join(summary_sentences)


async def extract_error_cards(text: str) -> list:
    """Extract error information to create cards

    This is a simplified version. In production, use AI to extract structured data
    """
    errors = []

    # Simple pattern matching for error-like structures
    # Look for patterns like "Error:", "Issue:", etc.
    error_patterns = [
        r'(?:Error|Issue|Problem):\s*([^\n]+)',
        r'Service:\s*([^\n]+)',
        r'Severity:\s*(critical|high|medium|low)',
    ]

    # This is a basic implementation - in production, use AI for better extraction
    lines = text.split('\n')
    current_error = {}

    for i, line in enumerate(lines):
        if 'error' in line.lower() or 'issue' in line.lower():
            if current_error:
                errors.append(current_error)
            current_error = {
                'id': f'extracted-{len(errors)+1}',
                'service': 'Unknown',
                'error_type': line.strip(),
                'count': 1,
                'severity': 'medium',
                'description': line.strip(),
                'root_cause': '',
                'resolution_status': 'investigating',
                'action_items': [],
                'responsible_team': 'TBD'
            }

    if current_error:
        errors.append(current_error)

    # If no errors found, create a placeholder
    if not errors:
        errors.append({
            'id': 'manual-entry-required',
            'service': 'Multiple',
            'error_type': 'Review uploaded document',
            'count': 0,
            'severity': 'medium',
            'description': 'Please review the uploaded document and manually create error cards',
            'root_cause': 'Automated extraction could not identify specific errors',
            'resolution_status': 'investigating',
            'action_items': ['Review uploaded document', 'Create specific error entries'],
            'responsible_team': 'Review Team'
        })

    return errors


@router.post("/upload-review")
async def upload_review_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload and process a PDF or Markdown file to create a SECA review"""
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_ext = file.filename.lower().split('.')[-1]
        if file_ext not in ['pdf', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail="Only PDF and Markdown files are supported"
            )

        # Read file content
        content = await file.read()

        # Extract text based on file type
        if file_ext == 'pdf':
            text = await extract_text_from_pdf(content)
        else:
            text = await extract_text_from_markdown(content)

        # Generate summary
        summary = await generate_summary(text)

        # Extract error cards
        errors = await extract_error_cards(text)

        return {
            "summary": summary,
            "errors": errors,
            "original_text": text[:1000],  # First 1000 chars for reference
            "filename": file.filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process uploaded file", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@router.post("/upload-seca-xlsx")
async def upload_seca_xlsx(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    headless: bool = True,
    sync: bool = False,
) -> JSONResponse:
    """Accept XLSX and schedule SECA processing job.

    If REDIS_URL is configured and rq is available, enqueue to RQ. Otherwise schedule in-process background task.
    Returns a job id and status URL.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = file.filename.lower().split('.')[-1]
    if ext not in ("xlsx", "xlsm", "xls"):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx/.xlsm/.xls) are supported")

    # Save uploaded file to temp location
    try:
        content = await file.read()

        # Enforce max upload size (env or default 10MB)
        max_bytes = int(os.getenv('MAX_UPLOAD_SIZE_BYTES', str(10 * 1024 * 1024)))
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail=f"Uploaded file exceeds max size of {max_bytes} bytes")

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp_path = tmp.name
            tmp.write(content)
    except Exception as e:
        logger.exception("Failed to save uploaded XLSX", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    job_id = str(uuid.uuid4())
    # Simple in-memory job store for BackgroundTasks fallback
    if 'JOBS' not in globals():
        globals()['JOBS'] = {}

    # If client requested synchronous processing, run it here and stream zip
    if sync:
        try:
            from app.tasks.seca_tasks import process_seca_file
            zip_path = await asyncio.to_thread(process_seca_file, tmp_path, file.filename)
            if zip_path and os.path.exists(zip_path):
                f = open(zip_path, 'rb')
                return StreamingResponse(f, media_type='application/zip', headers={
                    'Content-Disposition': f'attachment; filename="{os.path.basename(zip_path)}"'
                })
            else:
                raise HTTPException(status_code=500, detail='Processing failed')
        except HTTPException:
            raise
        except Exception as e:
            logger.exception('Synchronous processing failed', error=str(e))
            raise HTTPException(status_code=500, detail=f'Synchronous processing failed: {e}')

    # Try to enqueue to RQ if REDIS_URL is set
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        try:
            redis_conn = Redis.from_url(redis_url)
            q = RQQueue('seca', connection=redis_conn)
            # Import task function
            from app.tasks.seca_tasks import process_seca_file
            job = q.enqueue(process_seca_file, tmp_path, file.filename)
            # store mapping from our uuid to rq job id
            globals()['JOBS'][job_id] = {
                'status': 'queued',
                'rq_id': job.get_id(),
                'result_path': None,
            }
            status_url = f"/correlation-engine/api/seca-jobs/{job_id}"
            return JSONResponse({"job_id": job_id, "status_url": status_url})
        except Exception as e:
            logger.warning("Failed to enqueue to RQ, falling back to BackgroundTasks", error=str(e))

    # BackgroundTasks fallback: run in thread and store path in JOBS
    globals()['JOBS'][job_id] = {'status': 'running', 'result_path': None, 'error': None}

    def _bg_worker(path, filename, jid):
        try:
            from app.tasks.seca_tasks import process_seca_file
            zip_path = process_seca_file(path, filename)
            globals()['JOBS'][jid]['status'] = 'finished'
            globals()['JOBS'][jid]['result_path'] = zip_path
        except Exception as e:
            globals()['JOBS'][jid]['status'] = 'failed'
            globals()['JOBS'][jid]['error'] = str(e)

    # schedule background work
    if background_tasks is not None:
        background_tasks.add_task(_bg_worker, tmp_path, file.filename, job_id)
    else:
        # fallback: run in thread
        asyncio.create_task(asyncio.to_thread(_bg_worker, tmp_path, file.filename, job_id))

    status_url = f"/correlation-engine/api/seca-jobs/{job_id}"
    return JSONResponse({"job_id": job_id, "status_url": status_url})