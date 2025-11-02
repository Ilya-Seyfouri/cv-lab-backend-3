from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import supabase
import logging


logger = logging.getLogger(__name__)



security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Extract user from JWT token in Authorization header.
    Returns user dict with id, email, etc.
    """


    token = credentials.credentials

    try:
        # Verify token and get user
        user_response = supabase.auth.get_user(token)
        return user_response.user


    except Exception as e:

        logger.error(f"AUTH FAILED: {type(e).__name__}: {str(e)}")

        raise HTTPException(status_code=401, detail=str(e))