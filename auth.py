from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import supabase

security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Extract user from JWT token in Authorization header.
    Returns user dict with id, email, etc.
    """
    token = credentials.credentials

    print("=== AUTHENTICATION ===")
    print(f"Token received (first 20 chars): {token[:20]}...")

    try:
        # Verify token and get user
        user_response = supabase.auth.get_user(token)
        print(f"✅ Auth successful - User: {user_response.user.email}")
        return user_response.user

    except Exception as e:
        print(f"❌ Auth FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )