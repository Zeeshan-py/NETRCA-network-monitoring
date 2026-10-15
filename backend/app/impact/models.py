"""Typed, evidence-linked Phase 12 results."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.rca.models import EvidenceReference


class ImpactEntity(BaseModel):
    kind: Literal["DEVICE", "LINK", "SERVICE"]
    id: UUID
    classification: Literal["OBSERVED", "POTENTIAL"]
    evidence: list[EvidenceReference] = Field(default_factory=list)
    explanation: str


class ChainEdge(BaseModel):
    step: int
    source_kind: Literal["DEVICE", "LINK", "SERVICE"]
    source_id: UUID
    target_kind: Literal["DEVICE", "LINK", "SERVICE"]
    target_id: UUID
    relationship: Literal["LINK_ENDPOINT", "DEVICE_ADJACENCY", "HOSTS_SERVICE"]
    classification: Literal["POTENTIAL"] = "POTENTIAL"
    evidence: list[EvidenceReference] = Field(default_factory=list)
    explanation: str


class ImpactResult(BaseModel):
    incident_id: UUID
    rca_run_id: UUID
    status: Literal["ASSESSED", "INCONCLUSIVE"]
    candidate_target_kind: Literal["DEVICE", "LINK"] | None = None
    candidate_target_id: UUID | None = None
    entities: list[ImpactEntity] = Field(default_factory=list)
    chain: list[ChainEdge] = Field(default_factory=list)
    affected_devices: int = 0
    affected_links: int = 0
    affected_services: int = 0
    user_application_impact: Literal["UNKNOWN_UNVERIFIED"] = "UNKNOWN_UNVERIFIED"
    topology_input: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    analysis_version: Literal["IMPACT_RULES_V1"] = "IMPACT_RULES_V1"


class ImpactRun(BaseModel):
    id: UUID
    rca_run_id: UUID
    analysis_version: str
    input_fingerprint: str
    topology_fingerprint: str
    status: Literal["ASSESSED", "INCONCLUSIVE"]
    result: ImpactResult
    created_at: datetime
    last_analyzed_at: datetime


class ImpactResponse(BaseModel):
    success: Literal[True] = True
    data: ImpactRun
