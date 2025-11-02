from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import supabase
import logging, sys


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)




security = HTTPBearer()


async def get_current_user(request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Extract user from JWT token in Authorization header.
    Returns user dict with id, email, etc.
    """

    logger.debug("get_current_user called")
    logger.debug(f"Headers: {request.headers}")
    token = credentials.credentials

    try:
        # Verify token and get user
        user_response = await supabase.auth.get_user(token)
        return user_response.user


    except Exception as e:

        logger.error(f"AUTH FAILED: {type(e).__name__}: {str(e)}")

        raise HTTPException(status_code=401, detail=str(e))