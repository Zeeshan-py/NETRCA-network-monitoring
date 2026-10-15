from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NETRCA_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    cors_origins: str = ""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr | None = Field(default=None, validation_alias="DATABASE_URL")
    simulation_enabled: bool = False
    simulation_operation_timeout_seconds: int = Field(default=20, ge=1, le=60)
    topology_writes_enabled: bool = False
    pipeline_writes_enabled: bool = False
    fault_injection_enabled: bool = False
    anomaly_writes_enabled: bool = False
    correlation_writes_enabled: bool = False
    correlation_window_seconds: int = Field(default=300, ge=1, le=3600)
    correlation_max_age_minutes: int = Field(default=1440, ge=1, le=10080)
    rca_writes_enabled: bool = False
    rca_timing_window_seconds: int = Field(default=300, ge=1, le=3600)
    impact_writes_enabled: bool = False
    gemini_enabled: bool = False
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", pattern=r"^gemini-[A-Za-z0-9._-]+$")
    gemini_timeout_seconds: int = Field(default=15, ge=2, le=30)
    anomaly_latency_ms: float = Field(default=100, gt=0, le=10000)
    anomaly_packet_loss_percent: float = Field(default=5, gt=0, le=100)
    anomaly_min_availability_percent: float = Field(default=99, gt=0, le=100)
    anomaly_error_delta: int = Field(default=1, ge=1, le=10000)
    anomaly_max_age_minutes: int = Field(default=60, ge=1, le=1440)
    anomaly_history_hours: int = Field(default=24, ge=1, le=168)
    anomaly_max_history: int = Field(default=100, ge=20, le=200)
    anomaly_baseline_min_samples: int = Field(default=20, ge=10, le=100)
    anomaly_ml_enabled: bool = True
    anomaly_model_min_samples: int = Field(default=50, ge=30, le=200)
    anomaly_model_contamination: float = Field(default=0.05, ge=0.01, le=0.2)

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        for origin in (item.strip() for item in value.split(",") if item.strip()):
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("CORS origins must be comma-separated HTTP(S) origins")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
