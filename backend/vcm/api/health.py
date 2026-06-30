"""Health/readiness endpoint — also used as the container healthcheck."""

from __future__ import annotations

from fastapi import APIRouter

from vcm import __version__
from vcm.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "extract_model": settings.extract_model,
        "verify_model": settings.verify_model,
    }
