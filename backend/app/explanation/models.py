"""Versioned input and output contracts. Gemini sees claim IDs, never raw logs."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Section = Literal["summary", "observed_facts", "candidate_explanations",
                  "failure_chain_explanation", "impact_explanation", "uncertainties",
                  "missing_evidence", "limitations"]


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: Literal["EVENT", "ANOMALY", "TOPOLOGY", "RCA_RUN", "IMPACT_RUN"]
    source_id: UUID
    timestamp: datetime | None = None


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(pattern=r"^C[0-9]{3}$")
    section: Section
    text: str = Field(min_length=1, max_length=500)
    evidence_references: list[SourceReference] = Field(min_length=1, max_length=20)


class ExplanationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_version: Literal["EXPLANATION_INPUT_V1"] = "EXPLANATION_INPUT_V1"
    incident_id: UUID
    rca_run_id: UUID
    impact_run_id: UUID | None
    claims: list[Claim] = Field(min_length=1, max_length=80)


class ModelSelection(BaseModel):
    """The complete provider contract; prose and invented claims are forbidden."""
    model_config = ConfigDict(extra="forbid")
    ordered_claim_ids: list[str] = Field(min_length=1, max_length=80)


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explanation_version: Literal["EXPLANATION_V1"] = "EXPLANATION_V1"
    incident_id: UUID
    rca_run_id: UUID
    impact_run_id: UUID | None
    model_name: str
    summary: list[Claim]
    observed_facts: list[Claim]
    candidate_explanations: list[Claim]
    failure_chain_explanation: list[Claim]
    impact_explanation: list[Claim]
    uncertainties: list[Claim]
    missing_evidence: list[Claim]
    evidence_references: list[SourceReference]
    limitations: list[Claim]


class ExplanationResponse(BaseModel):
    success: Literal[True] = True
    data: Explanation
