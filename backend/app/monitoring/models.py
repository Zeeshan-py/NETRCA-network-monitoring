from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InterfaceReading(BaseModel):
    name: str
    status: Literal["UP", "DOWN", "UNKNOWN", "UNAVAILABLE"]
    operational_state: str | None = None
    rx_bytes: int | None = Field(default=None, ge=0)
    tx_bytes: int | None = Field(default=None, ge=0)
    rx_packets: int | None = Field(default=None, ge=0)
    tx_packets: int | None = Field(default=None, ge=0)
    rx_errors: int | None = Field(default=None, ge=0)
    tx_errors: int | None = Field(default=None, ge=0)
    error_code: str | None = None


class DeviceReading(BaseModel):
    name: str
    device_type: Literal["SWITCH", "HOST", "SERVER"]
    interfaces: list[InterfaceReading]


class LinkReading(BaseModel):
    source: str
    destination: str
    interface_source: str
    interface_destination: str
    status: Literal["UP", "DOWN", "UNKNOWN"]


class MonitoringSnapshot(BaseModel):
    observed_at: datetime
    topology_name: str
    network_state: Literal["RUNNING", "STOPPED", "UNAVAILABLE", "DISABLED"]
    collection_status: Literal["COMPLETE", "PARTIAL", "UNAVAILABLE"]
    counter_unit: Literal["bytes_and_packets"] = "bytes_and_packets"
    devices: list[DeviceReading]
    links: list[LinkReading]
    errors: list[str]


class ProbeRequest(BaseModel):
    source: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    destination: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    count: int = Field(default=2, ge=1, le=3)
    timeout_seconds: int = Field(default=2, ge=1, le=2)


class ProbeReading(BaseModel):
    observed_at: datetime
    source: str
    destination: str
    packets_sent: int | None = Field(default=None, ge=0)
    packets_received: int | None = Field(default=None, ge=0)
    packet_loss_percent: float | None = Field(default=None, ge=0, le=100)
    latency_ms: float | None = Field(default=None, ge=0)
    status: Literal["REACHABLE", "UNREACHABLE", "TIMEOUT", "UNAVAILABLE"]
    error_code: str | None = None


class MonitoringResponse(BaseModel):
    success: Literal[True] = True
    data: MonitoringSnapshot


class ProbeResponse(BaseModel):
    success: Literal[True] = True
    data: ProbeReading
