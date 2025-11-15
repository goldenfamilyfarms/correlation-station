"""
SECA Error Reviews API Routes
"""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from app.database import (
    get_all_reviews,
    get_review_by_id,
    create_review,
    update_review,
    delete_review,
)

logger = structlog.get_logger()

router = APIRouter()


class ErrorDetail(BaseModel):
    id: str
    service: str
    error_type: str
    count: int
    severity: str
    description: str
    root_cause: str
    resolution_status: str
    action_items: List[str]
    responsible_team: str


class CreateReviewRequest(BaseModel):
    period: str
    summary: str
    errors: List[ErrorDetail]


class UpdateReviewRequest(BaseModel):
    summary: str


@router.get("/seca-reviews")
async def list_reviews() -> List[Dict[str, Any]]:
    """Get all SECA error reviews"""
    try:
        reviews = await get_all_reviews()
        return reviews
    except Exception as e:
        logger.exception("Failed to get reviews", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve reviews")


@router.get("/seca-reviews/{review_id}")
async def get_review(review_id: int) -> Dict[str, Any]:
    """Get a specific SECA error review"""
    try:
        review = await get_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get review", review_id=review_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve review")


@router.post("/seca-reviews", status_code=201)
async def create_new_review(request: CreateReviewRequest) -> Dict[str, Any]:
    """Create a new SECA error review"""
    try:
        errors_dict = [error.dict() for error in request.errors]
        review = await create_review(
            period=request.period,
            summary=request.summary,
            errors=errors_dict,
        )
        return review
    except Exception as e:
        logger.exception("Failed to create review", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create review")


@router.put("/seca-reviews/{review_id}")
async def update_existing_review(
    review_id: int, request: UpdateReviewRequest
) -> Dict[str, Any]:
    """Update an existing SECA error review"""
    try:
        review = await update_review(review_id, request.summary)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update review", review_id=review_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update review")


@router.delete("/seca-reviews/{review_id}", status_code=204)
async def delete_existing_review(review_id: int):
    """Delete a SECA error review"""
    try:
        deleted = await delete_review(review_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Review not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete review", review_id=review_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete review")
