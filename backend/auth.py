import os
import jwt
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

HOST_APP_JWT_SECRET = os.getenv("HOST_APP_JWT_SECRET", "dev-secret-key-12345")
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "true").lower() in ("true", "1", "yes")

security = HTTPBearer(auto_error=False)

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    """
    Validates JWT token provided by host app in Authorization header.
    Bypasses if DISABLE_AUTH=true.
    """
    if DISABLE_AUTH:
        return {
            "sub": "dev-user-123",
            "host_app": "demo-host",
            "roles": ["researcher"],
            "auth_disabled": True
        }

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, HOST_APP_JWT_SECRET, algorithms=["HS256", "RS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Host JWT token has expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid host JWT token: {str(e)}")
