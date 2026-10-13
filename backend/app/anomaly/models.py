"""API contracts for analysis of Phase 6 observations."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.pipeline.models import MetricIn


SUPPORTED_METRICS = frozenset({"LATENCY", "PACKET_LOSS", "AVAILABILITY", "INTERFACE_STATE",
                               "LINK_STATE", "RX_ERRORS", "TX_ERRORS"})
DetectionStatus = Literal["NORMAL", "ANOMALY", "INSUFFICIENT_DATA"]


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=20)
    observations: list[MetricIn] | None = Field(default=None, min_length=1, max_length=20)
    persist: bool = False

    @model_validator(mode="after")
    def valid_mode(self):
        if (self.metric_ids is None) == (self.observations is None):
            raise ValueError("Provide metric_ids or observations, not both")
        if self.observations is not None:
            if self.persist or any(item.source != "manual" for item in self.observations):
                raise ValueError("Inline observations must be manual and cannot be persisted")
            if any(item.metric_type not in SUPPORTED_METRICS for item in self.observations):
                raise ValueError("Inline observation has an unsupported detection metric")
        return self


class DetectionResult(BaseModel):
    metric_id: UUID | None = None
    observation_key: str
    device_id: UUID | None = None
    link_id: UUID | None = None
    metric_type: str
    value: Decimal
    unit: str
    observed_at: datetime
    status: DetectionStatus
    method: Literal["THRESHOLD", "BASELINE", "ISOLATION_FOREST", "NONE"]
    reason: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    score: float | None = None
    score_kind: str | None = None
    support: dict = Field(default_factory=dict)
    baseline_samples: int = 0
    anomaly_id: UUID | None = None
    persistence: Literal["NOT_REQUESTED", "PERSISTED", "EXISTING", "UNAVAILABLE", "NOT_ELIGIBLE"] = "NOT_REQUESTED"
