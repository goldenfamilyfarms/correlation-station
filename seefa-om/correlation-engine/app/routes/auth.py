"""Basic authentication dependency"""
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

security = HTTPBasic(auto_error=False)


async def verify_basic_auth(credentials: HTTPBasicCredentials = Security(security)) -> bool:
    """
    Verify Basic Auth credentials if enabled

    Returns True if auth is disabled or credentials are valid.
    Raises HTTPException if auth is enabled and credentials are invalid.
    """
    # If BasicAuth is disabled, allow all requests
    if not settings.enable_basic_auth:
        return True

    # BasicAuth is enabled but no credentials provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify credentials
    correct_username = secrets.compare_digest(
        credentials.username, settings.basic_auth_user or ""
    )
    correct_password = secrets.compare_digest(
        credentials.password, settings.basic_auth_pass or ""
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return True