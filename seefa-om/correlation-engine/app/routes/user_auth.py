"""
User Authentication and Progress Tracking API Routes
Handles user registration, login, and tutorial progress
"""
import hashlib
import secrets
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import structlog

from app.database import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    mark_tutorial_complete,
    get_user_progress,
    is_tutorial_complete,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


# ====================
# REQUEST/RESPONSE MODELS
# ====================

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str


class TutorialCompleteRequest(BaseModel):
    tutorial_id: str


class TutorialProgressResponse(BaseModel):
    tutorial_id: str
    completed: bool
    completed_at: str


# ====================
# PASSWORD HASHING
# ====================

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        salt, pwd_hash = password_hash.split("$")
        computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return computed_hash == pwd_hash
    except Exception:
        return False


# ====================
# AUTH ENDPOINTS
# ====================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegisterRequest):
    """
    Register a new user

    Creates a new user account with hashed password.
    Returns the user object without password.
    """
    try:
        # Generate user ID
        user_id = secrets.token_urlsafe(16)

        # Hash password
        password_hash = hash_password(request.password)

        # Create user
        user = await create_user(
            user_id=user_id,
            username=request.username,
            email=request.email,
            password_hash=password_hash,
        )

        logger.info("User registered", username=request.username, user_id=user_id)

        return UserResponse(**user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Failed to register user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


@router.post("/login", response_model=UserResponse)
async def login_user(request: UserLoginRequest):
    """
    Login user

    Verifies username and password.
    Returns the user object on successful authentication.
    """
    try:
        # Get user by username
        user = await get_user_by_username(request.username)

        if not user:
            logger.warning("Login failed - user not found", username=request.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            logger.warning("Login failed - invalid password", username=request.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        logger.info("User logged in", username=request.username, user_id=user["id"])

        # Return user without password_hash
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """
    Get user by ID

    Returns user information without password.
    """
    user = await get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(**user)


# ====================
# TUTORIAL PROGRESS ENDPOINTS
# ====================

@router.post("/user/{user_id}/tutorial/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_tutorial(user_id: str, request: TutorialCompleteRequest):
    """
    Mark a tutorial as complete for a user

    Creates or updates the tutorial progress record.
    """
    try:
        # Verify user exists
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Mark tutorial complete
        await mark_tutorial_complete(user_id, request.tutorial_id)

        logger.info(
            "Tutorial marked complete",
            user_id=user_id,
            tutorial_id=request.tutorial_id,
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark tutorial complete", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update progress",
        )


@router.get("/user/{user_id}/progress", response_model=List[TutorialProgressResponse])
async def get_progress(user_id: str):
    """
    Get all tutorial progress for a user

    Returns list of completed tutorials.
    """
    try:
        # Verify user exists
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get progress
        progress = await get_user_progress(user_id)

        return [TutorialProgressResponse(**p) for p in progress]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get progress", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve progress",
        )


@router.get("/user/{user_id}/tutorial/{tutorial_id}/status")
async def get_tutorial_status(user_id: str, tutorial_id: str):
    """
    Check if a specific tutorial is complete

    Returns { "completed": true/false }
    """
    try:
        completed = await is_tutorial_complete(user_id, tutorial_id)
        return {"completed": completed}

    except Exception as e:
        logger.error("Failed to check tutorial status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check status",
        )
