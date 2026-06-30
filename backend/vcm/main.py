"""FastAPI application factory (plan/04-api-and-frontend.md).

At the scaffold stage only the health router is mounted; domain routers
(graph, evidence, cards, analytics, pipeline, review) land in later Phase 0/1 tasks.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vcm import __version__
from vcm.api.health import router as health_router
from vcm.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Value Chain Map API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # All API routes are served under /api (the frontend dev server proxies /api).
    app.include_router(health_router, prefix="/api")
    return app


app = create_app()
