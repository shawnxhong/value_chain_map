"""Runtime configuration (plan/README.md §Cross-cutting).

Values come from environment variables prefixed with ``VCM_`` (e.g.
``VCM_DATABASE_URL``) or an ``.env`` file in the working directory.

Anthropic credentials are intentionally NOT held here: the Anthropic SDK resolves
them from ``ANTHROPIC_API_KEY`` or an ``ant`` profile at call time
(see plan/02-pipeline-and-llm.md). Only model ids are configured here, so they can
be swapped without code edits.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VCM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- database ---
    database_url: str = "postgresql+psycopg://vcm:vcm@localhost:5432/vcm"

    # --- LLM (ids only; auth via ANTHROPIC_API_KEY / ant profile) ---
    extract_model: str = "claude-sonnet-4-6"
    verify_model: str = "claude-opus-4-8"

    # --- object storage (raw source documents) ---
    storage_dir: str = "./data/objects"

    # --- analytics / freshness ---
    staleness_warn_months: int = 12

    # --- app ---
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""
    return Settings()
