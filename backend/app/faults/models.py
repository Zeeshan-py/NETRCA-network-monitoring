from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


FaultType = Literal["INTERFACE_FAILURE", "LINK_FAILURE", "PACKET_LOSS", "HIGH_LATENCY"]
FaultStatus = Literal["ACTIVE", "COMPLETED", "CANCELLED"]


class FaultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fault_type: FaultType
    device: str | None = Field(default=None, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    interface: str | None = Field(default=None, max_length=15, pattern=r"^[A-Za-z0-9_.-]+$")
    source: str | None = Field(default=None, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    destination: str | None = Field(default=None, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    packet_loss_percent: Decimal | None = Field(default=None, ge=1, le=100, allow_inf_nan=False)
    latency_ms: Decimal | None = Field(default=None, ge=1, le=250, allow_inf_nan=False)
    duration_seconds: int = Field(default=30, ge=1, le=300)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"

    @model_validator(mode="after")
    def valid_target(self):
        if self.fault_type == "LINK_FAILURE":
            if not self.source or not self.destination or self.source == self.destination or any(
                x is not None for x in (self.device, self.interface, self.packet_loss_percent, self.latency_ms)
            ):
                raise ValueError("Link faults require two distinct endpoints only")
        else:
            if not self.device or not self.interface or self.source or self.destination:
                raise ValueError("Interface faults require a device and interface only")
            if self.fault_type == "PACKET_LOSS":
                if self.packet_loss_percent is None or self.latency_ms is not None:
                    raise ValueError("Packet loss requires only packet_loss_percent")
            elif self.fault_type == "HIGH_LATENCY":
                if self.latency_ms is None or self.packet_loss_percent is not None:
                    raise ValueError("High latency requires only latency_ms")
            elif self.packet_loss_percent is not None or self.latency_ms is not None:
                raise ValueError("Interface down has no traffic-shaping parameter")
        return self


class FaultRecord(BaseModel):
    id: UUID
    fault_type: FaultType
    status: FaultStatus
    target: dict[str, str]
    parameters: dict[str, str | int]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    started_at: datetime
    expires_at: datetime
    ended_at: datetime | None = None
    end_reason: Literal["RECOVERED", "CANCELLED", "EXPIRED", "LAB_STOPPED", "APPLY_FAILED"] | None = None
    restoration_result: Literal["PENDING", "SUCCEEDED", "FAILED"] = "PENDING"
    error_code: str | None = None
    storage_status: Literal["SYNCED", "UNMAPPED", "UNAVAILABLE"] = "UNAVAILABLE"
