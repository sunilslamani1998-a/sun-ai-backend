import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import settings

bearer_scheme = HTTPBearer(auto_error=False, description="SUN.AI API bearer token")


def get_api_token() -> str:
    return settings.sunai_api_token.get_secret_value().strip()


def validate_api_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> str:
    expected_token = get_api_token()
    if not expected_token:
        raise HTTPException(status_code=503, detail="API authentication is not configured.")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    if not secrets.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(status_code=401, detail="Invalid authentication token.", headers={"WWW-Authenticate": "Bearer"})
    return "owner"

AuthenticatedUser = Annotated[str, Depends(validate_api_token)]
