from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Literal

Severity = Literal["LOW", "MEDIUM", "HIGH"]

class PondOut(BaseModel):
    id: int
    name: str
    species: str

class ReadingCreate(BaseModel):
    pond_id: int
    dissolved_oxygen: float = Field(..., ge=0)
    temperature: float = Field(..., ge=-5, le=60)
    ammonia: float = Field(..., ge=0)
    ph: float = Field(..., ge=0, le=14)
    turbidity: float = Field(0.0, ge=0)

class ReadingOut(BaseModel):
    id: int
    pond_id: int
    dissolved_oxygen: float
    temperature: float
    ammonia: float
    ph: float
    turbidity: float
    health_score: float
    do_risk: float
    nh3_risk: float
    created_at: datetime

class HealthOut(BaseModel):
    pond_id: int
    health_score: float
    do_risk: float
    nh3_risk: float
    status: str  # GOOD | WATCH | CRITICAL

class AlertOut(BaseModel):
    id: int
    pond_id: int
    message: str
    severity: Severity
    resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None

class TimeseriesPoint(BaseModel):
    t: datetime
    dissolved_oxygen: float
    ammonia: float
    temperature: float
    ph: float
    health_score: float

class TimeseriesOut(BaseModel):
    pond_id: int
    points: List[TimeseriesPoint]
