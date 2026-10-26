import os
import secrets
from fastapi import Header, HTTPException

API_TOKEN = os.getenv("SUNAI_API_TOKEN", "")


def require_auth(authorization: str | None = Header(default=None)):
    if not API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="SUNAI_API_TOKEN is not configured."
        )

    expected = f"Bearer {API_TOKEN}"
    if not authorization or not secrets.compare_digest(
        authorization, expected
    ):
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )
    return "owner"


def require_approval(approved: bool):
    if not approved:
        raise HTTPException(
            status_code=403,
            detail="Explicit approval is required."
        )
