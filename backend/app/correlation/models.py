from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CorrelationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_ids: list[UUID] = Field(default_factory=list, max_length=100)
    anomaly_ids: list[UUID] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def bounded_total(self):
        if len(self.event_ids) + len(self.anomaly_ids) > 100:
            raise ValueError("At most 100 evidence IDs are accepted")
        return self
