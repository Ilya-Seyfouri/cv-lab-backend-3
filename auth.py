from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import supabase
import logging, sys



logging.basicConfig(
    level=logging.DEBUG,   # switch to INFO if DEBUG too noisy
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)




security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
):
    logger = logging.getLogger("auth")
    # log raw headers (careful not to leak tokens in public logs)
    auth_header = None
    try:
        auth_header = request.headers.get("authorization")
    except Exception:
        print("hi")

    logger.debug("get_current_user called; Authorization header present=%s", bool(auth_header))

    try:
        token = credentials.credentials
        logger.debug("Token length: %d", len(token) if token else 0)

        user_response = await supabase.auth.get_user(token)
        logger.debug("supabase.get_user response: %r", getattr(user_response, "__dict__", str(user_response)))
        # adapt depending on response shape:
        user = getattr(user_response, "user", user_response)
        logger.info("Authenticated user id=%s", getattr(user, "id", None))
        return user

    except Exception as e:
        logger.exception("AUTH FAILED")
        # hide sensitive internal message from client; return generic
        raise HTTPException(status_code=401, detail="Not authenticated")
