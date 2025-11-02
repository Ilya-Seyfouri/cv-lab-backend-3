from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import supabase
import logging, sys

logger = logging.getLogger("uvicorn.error")  # ensures it prints in Railway logs
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials if credentials else None
    logger.info(f"Authorization header token received: {token}")

    if not token:
        logger.error("No token provided in request")
        raise HTTPException(status_code=403, detail="No token provided")

    try:
        user_response = await supabase.auth.get_user(token)
        if not user_response.user:
            logger.error("Supabase returned no user for this token")
            raise HTTPException(status_code=403, detail="Invalid token")
        logger.info(f"Authenticated user id: {user_response.user.id}")
        return user_response.user
    except Exception as e:
        logger.exception(f"Supabase authentication failed: {str(e)}")
        raise HTTPException(status_code=403, detail="Authentication failed")