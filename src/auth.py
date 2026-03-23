"""
Supabase Auth Integration
Handles JWT verification for protected API routes.
"""
import os
import logging
from functools import wraps
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify Supabase JWT token and return user info.
    If no auth configured (local dev), allow all requests.
    """
    # Skip auth if Supabase not configured (local dev mode)
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return {"id": "local-dev", "email": "dev@localhost", "role": "admin"}

    if not credentials:
        raise HTTPException(401, "Not authenticated")

    token = credentials.credentials

    try:
        # Verify token with Supabase
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise HTTPException(401, "Invalid or expired token")

        user = response.json()
        return {
            "id": user.get("id"),
            "email": user.get("email"),
            "role": user.get("role", "authenticated"),
        }

    except requests.Timeout:
        raise HTTPException(503, "Auth service timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth verification failed: {e}")
        raise HTTPException(401, "Authentication failed")
