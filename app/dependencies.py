# app/dependencies.py

from app.db.supabase_client import get_supabase_client_for_user
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


def get_client(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    jwt = credentials.credentials
    return get_supabase_client_for_user(jwt)
