from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EnvironmentReport(BaseModel):
    available: bool
    code: str


class NetworkStatus(BaseModel):
    available: bool
    state: Literal["DISABLED", "UNAVAILABLE", "STOPPED", "STARTING", "RUNNING", "STOPPING", "RESETTING", "FAILED"]
    topology_name: str
    started_at: datetime | None = None
    device_count: int = 0
    link_count: int = 0
    operation: str | None = None
    last_operation: str | None = None
    last_result: Literal["SUCCEEDED", "FAILED"] | None = None
    detail: str | None = None


class DeviceView(BaseModel):
    id: str
    name: str
    device_type: Literal["SWITCH", "HOST", "SERVER"]
    ip_address: str | None = None
    state: Literal["PRESENT"] = "PRESENT"


class LinkView(BaseModel):
    id: str
    source: str
    destination: str
    status: Literal["UP", "DOWN"]
    interface_source: str
    interface_destination: str


class TopologyView(BaseModel):
    topology_name: str
    nodes: list[DeviceView]
    links: list[LinkView]


class ConnectivityView(BaseModel):
    hosts: list[str]
    packet_loss_percent: float
    connected: bool


class StatusResponse(BaseModel):
    success: Literal[True] = True
    data: NetworkStatus


class TopologyResponse(BaseModel):
    success: Literal[True] = True
    data: TopologyView


class ConnectivityResponse(BaseModel):
    success: Literal[True] = True
    data: ConnectivityView


class OperationResponse(BaseModel):
    success: Literal[True] = True
    data: NetworkStatus
    message: str
