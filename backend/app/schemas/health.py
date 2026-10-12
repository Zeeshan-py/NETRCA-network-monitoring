from typing import Literal

from pydantic import BaseModel


class HealthData(BaseModel):
    api: Literal["UP"] = "UP"


class HealthResponse(BaseModel):
    success: Literal[True] = True
    data: HealthData
