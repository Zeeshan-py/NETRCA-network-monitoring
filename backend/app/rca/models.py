"""Typed Phase 11 response and internal evidence contracts."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["EVENT", "ANOMALY"]
    id: UUID
    observed_at: datetime | None = None
    device_id: UUID | None = None
    link_id: UUID | None = None
    event_type: str | None = None
    event_status: str | None = None
    metric_id: UUID | None = None
    metric_type: str | None = None
    metric_value: Decimal | None = None
    source_event_id: UUID | None = None


class EvidenceReference(BaseModel):
    source_type: Literal["EVENT", "ANOMALY", "TOPOLOGY"]
    source_id: UUID
    timestamp: datetime | None = None
    metric_id: UUID | None = None
    reason: str


class RuleContribution(BaseModel):
    rule: str
    points: int
    evidence: list[EvidenceReference] = Field(default_factory=list)


class Candidate(BaseModel):
    cause_type: Literal["LINK_FAILURE", "INTERFACE_FAILURE", "DEVICE_UNAVAILABLE"]
    target_kind: Literal["LINK", "DEVICE"]
    target_id: UUID
    score: int
    score_kind: Literal["UNCALIBRATED_RULE_POINTS"] = "UNCALIBRATED_RULE_POINTS"
    explanation: str
    contributions: list[RuleContribution]
    supporting_evidence: list[EvidenceReference]
    contradictory_evidence: list[EvidenceReference]
    limitations: list[str]


class AnalysisResult(BaseModel):
    incident_id: UUID
    status: Literal["CANDIDATES", "INCONCLUSIVE"]
    candidates: list[Candidate]
    limitations: list[str]
    evidence_count: int
    analysis_version: Literal["RULES_V1"] = "RULES_V1"


class RcaRun(BaseModel):
    id: UUID
    incident_id: UUID
    analysis_version: str
    input_fingerprint: str
    status: Literal["CANDIDATES", "INCONCLUSIVE"]
    result: AnalysisResult
    created_at: datetime
    last_analyzed_at: datetime


class RcaResponse(BaseModel):
    success: Literal[True] = True
    data: RcaRun
