"""
File upload and processing for SECA reviews
"""
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
import structlog
import io
import re

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
