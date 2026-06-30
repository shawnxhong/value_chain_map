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

from vcm.models.enums import LLMProvider


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VCM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- database ---
    database_url: str = "postgresql+psycopg://vcm:vcm@localhost:5432/vcm"

    # --- LLM (provider + model ids only; auth via per-provider env keys) ---
    # Anthropic is the default; OpenAI/DeepSeek are opt-in per role (plan/02 §LLM layer).
    # Keys resolve from env at call time: ANTHROPIC_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY.
    extract_provider: LLMProvider = LLMProvider.anthropic
    extract_model: str = "claude-sonnet-4-6"
    verify_provider: LLMProvider = LLMProvider.anthropic
    verify_model: str = "claude-opus-4-8"
    deepseek_base_url: str = "https://api.deepseek.com"
    # SDK auto-retries 429/5xx/connection errors with exponential backoff (plan/02).
    llm_max_retries: int = 2

    # --- object storage (raw source documents) ---
    storage_dir: str = "./data/objects"

    # --- ingestion / parsing ---
    # SEC requires a descriptive User-Agent with contact info on EDGAR requests.
    edgar_user_agent: str = "vcm-research vcm@example.com"
    # Target chunk size in characters (~4 chars/token => ~1.5k tokens) for LLM extraction.
    chunk_target_chars: int = 6000

    # --- analytics / freshness ---
    staleness_warn_months: int = 12

    # --- app ---
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""
    return Settings()
