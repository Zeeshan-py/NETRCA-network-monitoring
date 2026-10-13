"""Strict records for the evidence tables in the Phase 2 schema."""
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MetricType = Literal["LATENCY", "PACKET_LOSS", "AVAILABILITY", "INTERFACE_STATE", "LINK_STATE",
                     "RX_BYTES", "TX_BYTES", "RX_PACKETS", "TX_PACKETS", "RX_ERRORS", "TX_ERRORS"]
EventType = Literal["DEVICE_UNAVAILABLE", "INTERFACE_FAILURE", "LINK_FAILURE",
                    "PROBE_FAILED", "PROBE_TIMEOUT", "COLLECTION_FAILURE"]
EventSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
LogSeverity = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
_UNITS = {"LATENCY": "ms", "PACKET_LOSS": "%", "AVAILABILITY": "%", "INTERFACE_STATE": "state", "LINK_STATE": "state",
          "RX_BYTES": "bytes", "TX_BYTES": "bytes", "RX_PACKETS": "packets", "TX_PACKETS": "packets",
          "RX_ERRORS": "packets", "TX_ERRORS": "packets"}
_SENSITIVE = re.compile(r"(?i)(password|passwd|secret|token|api[_ -]?key|authorization|bearer|"
                        r"postgres(?:ql)?://|supabase\.co|BEGIN [A-Z ]*PRIVATE KEY)")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    result = value.astimezone(timezone.utc)
    if result > datetime.now(timezone.utc).replace(microsecond=999999):
        raise ValueError("Future observations are not accepted")
    return result


class MetricIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: UUID | None = None
    link_id: UUID | None = None
    metric_type: MetricType
    value: Decimal = Field(ge=0, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=16)
    timestamp: datetime
    source: Literal["mininet_snapshot", "mininet_probe", "manual"]
    observation_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9:_.-]+$")
    interface: str | None = Field(default=None, max_length=15, pattern=r"^[A-Za-z0-9_.-]+$")
    target: str | None = Field(default=None, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("timestamp")
    @classmethod
    def valid_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def valid_measurement(self):
        if (self.device_id is None) == (self.link_id is None):
            raise ValueError("Metric requires exactly one device or link")
        if self.unit != _UNITS[self.metric_type]:
            raise ValueError("Unit does not match metric type")
        if self.metric_type in {"PACKET_LOSS", "AVAILABILITY"} and self.value > 100:
            raise ValueError("Percentage exceeds 100")
        if self.metric_type in {"INTERFACE_STATE", "LINK_STATE"} and self.value not in {0, 1}:
            raise ValueError("State must be zero or one")
        if self.metric_type in {"RX_BYTES", "TX_BYTES", "RX_PACKETS", "TX_PACKETS", "RX_ERRORS", "TX_ERRORS"}:
            if self.value != self.value.to_integral_value() or self.interface is None:
                raise ValueError("Counters require an interface and whole-number value")
        if self.metric_type == "INTERFACE_STATE" and self.interface is None:
            raise ValueError("Interface state requires an interface")
        if self.metric_type in {"INTERFACE_STATE", "RX_BYTES", "TX_BYTES", "RX_PACKETS", "TX_PACKETS", "RX_ERRORS", "TX_ERRORS"} and self.device_id is None:
            raise ValueError("Interface measurements require a device")
        if self.metric_type == "LINK_STATE" and self.link_id is None:
            raise ValueError("Link state requires a link")
        return self


class LogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: UUID | None = None
    service_id: UUID | None = None
    severity: LogSeverity
    event_type: str | None = Field(default=None, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")
    message: str = Field(min_length=1, max_length=512)
    source: Literal["netrca", "mininet", "operator"]
    timestamp: datetime
    observation_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9:_.-]+$")

    @field_validator("timestamp")
    @classmethod
    def valid_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def valid_log(self):
        if not self.device_id and not self.service_id:
            raise ValueError("Log requires a device or service")
        if not self.message.strip() or _SENSITIVE.search(self.message):
            raise ValueError("Log message is empty or may contain sensitive data")
        if "\n" in self.message or "\r" in self.message:
            raise ValueError("Multiline command output is not accepted")
        return self


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: UUID | None = None
    link_id: UUID | None = None
    event_type: EventType
    severity: EventSeverity
    source: Literal["mininet_snapshot", "mininet_probe", "netrca", "operator"]
    timestamp: datetime
    dedup_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9:_.-]+$")
    message: str = Field(min_length=1, max_length=256)

    @field_validator("timestamp")
    @classmethod
    def valid_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def valid_event(self):
        if self.event_type != "COLLECTION_FAILURE" and not (self.device_id or self.link_id):
            raise ValueError("Event requires a device or link")
        if not self.message.strip() or "\n" in self.message or "\r" in self.message or _SENSITIVE.search(self.message):
            raise ValueError("Event message must be one nonempty line")
        return self
