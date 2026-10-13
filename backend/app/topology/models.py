from datetime import datetime
from ipaddress import ip_interface
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


DeviceType = Literal["ROUTER", "SWITCH", "SERVER", "HOST", "DNS"]
DeviceStatus = Literal["HEALTHY", "WARNING", "DOWN", "PRESENT"]
LinkStatus = Literal["UP", "DEGRADED", "DOWN"]


class Device(BaseModel):
    id: UUID
    name: str
    device_type: DeviceType
    status: DeviceStatus
    ip_address: str | None = None
    mac_address: str | None = None
    hostname: str | None = None
    is_active: bool = True
    metadata: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Link(BaseModel):
    id: UUID
    source_device_id: UUID
    destination_device_id: UUID
    status: LinkStatus
    bandwidth_mbps: float | None = None
    latency_ms: float | None = None
    packet_loss_percent: float | None = None
    interface_source: str | None = None
    interface_destination: str | None = None
    metadata: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    device_type: DeviceType
    status: Literal["HEALTHY", "WARNING", "DOWN"]
    ip_address: str | None = None
    mac_address: str | None = None
    hostname: str | None = None
    metadata: dict | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Device name must not be blank")
        return value

    @field_validator("ip_address")
    @classmethod
    def valid_ip(cls, value: str | None) -> str | None:
        if value is not None:
            ip_interface(value)
        return value


class LinkCreate(BaseModel):
    source_device_id: UUID
    destination_device_id: UUID
    status: LinkStatus
    bandwidth_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    packet_loss_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    interface_source: str | None = None
    interface_destination: str | None = None
    metadata: dict | None = None


class TopologyValidation(BaseModel):
    valid: bool
    errors: list[str]
    components: list[list[UUID]]


class Snapshot(BaseModel):
    id: UUID
    snapshot_time: datetime
    topology_data: dict
    reason: str | None = None
    created_at: datetime


class SnapshotCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
