"""Local-only configuration; no credentials, endpoints or cloud feature switches."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLAIMS_AI_",
        env_file=None,  # Opt in explicitly to a dotenv path; never discover credentials implicitly.
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )
    environment: Literal["local", "test"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    max_document_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
