import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import settings

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="SUN.AI API bearer token",
)

def get_api_token() -> str:
    return settings.sunai_api_token.get_secret_value().strip()

def validate_api_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    expected_token = get_api_token()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    supplied_token = credentials.credentials
    if not secrets.compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "owner"

AuthenticatedUser = Annotated[str, Depends(validate_api_token)]
