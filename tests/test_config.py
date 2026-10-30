from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.config import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("ENVIRONMENT", "LOG_LEVEL", "MAX_DOCUMENT_BYTES"):
        monkeypatch.delenv(f"CLAIMS_AI_{key}", raising=False)


def test_safe_defaults() -> None:
    settings = Settings()
    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.max_document_bytes == 10 * 1024 * 1024
    assert not any("credential" in key or "key" in key for key in Settings.model_fields)


def test_environment_and_constructor_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAIMS_AI_ENVIRONMENT", "test")
    monkeypatch.setenv("CLAIMS_AI_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CLAIMS_AI_MAX_DOCUMENT_BYTES", "2048")
    assert Settings().environment == "test"
    assert Settings().max_document_bytes == 2048
    assert Settings(log_level="ERROR").log_level == "ERROR"


@pytest.mark.parametrize(
    "key,value",
    [
        ("ENVIRONMENT", "production"),
        ("LOG_LEVEL", "TRACE"),
        ("MAX_DOCUMENT_BYTES", "0"),
        ("MAX_DOCUMENT_BYTES", "52428801"),
        ("MAX_DOCUMENT_BYTES", "not-an-integer"),
    ],
)
def test_invalid_environment_settings(
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: str,
) -> None:
    monkeypatch.setenv(f"CLAIMS_AI_{key}", value)
    with pytest.raises(ValidationError):
        Settings()


def test_dotenv_is_opt_in_and_environment_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("CLAIMS_AI_LOG_LEVEL=ERROR\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert Settings().log_level == "INFO"
    assert Settings(_env_file=dotenv).log_level == "ERROR"
    monkeypatch.setenv("CLAIMS_AI_LOG_LEVEL", "WARNING")
    assert Settings(_env_file=dotenv).log_level == "WARNING"


def test_settings_are_immutable() -> None:
    with pytest.raises(ValidationError):
        Settings().environment = "test"  # type: ignore[misc]
