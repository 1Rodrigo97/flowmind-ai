"""Shared API dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


def require_automation_token(authorization: str | None = Header(default=None)) -> None:
    """Validate the automation service token on automation endpoints.

    n8n sends ``Authorization: Bearer <token>``. If no token is configured
    (local dev), auth is disabled. The token is never stored in the exported
    workflow -- it lives in an n8n credential/variable.
    """
    expected = settings.automation_token
    if not expected:
        return  # auth disabled in dev
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid automation token")
