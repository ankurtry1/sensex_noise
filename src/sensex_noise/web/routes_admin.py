from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import Settings, load_settings


router = APIRouter(prefix="/admin", tags=["admin"])


def get_settings() -> Settings:
    return load_settings()


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> Settings:
    expected = settings.admin_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_TOKEN is not configured",
        )

    supplied = x_admin_token or ""
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            supplied = value.strip()

    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return settings


@router.get("/status")
def status_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    record = TokenStore(settings.token_store_path).read_today()
    return {
        "token_store": {
            "has_today_token": record is not None,
            "metadata": record.safe_metadata() if record is not None else None,
        },
        "paths": {
            "data_dir": str(settings.data_dir),
            "logs_dir": str(settings.logs_dir),
            "runtime_dir": str(settings.runtime_dir),
            "token_store_path": str(settings.token_store_path),
        },
    }
