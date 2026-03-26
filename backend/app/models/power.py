from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class PowerReading(BaseModel):
    """Single power reading at a point in time"""
    timestamp: float
    watts: float
    voltage: Optional[float] = None
    current: Optional[float] = None
    source: str  # 'battery', 'ac_adapter', 'ipmi', 'estimated'


class PowerMetrics(BaseModel):
    """Current power metrics for WebSocket/API"""
    timestamp: float
    watts: float
    voltage: Optional[float] = None
    current: Optional[float] = None
    source: str
    total_kwh: float  # Accumulated since logging started
    uptime_hours: float


class PowerHistoryRequest(BaseModel):
    start_date: datetime
    end_date: datetime


class PowerHistoryResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    total_kwh: float
    avg_watts: float
    max_watts: float
    min_watts: float
    readings_count: int
    hours_span: float


class PowerReadingEntry(BaseModel):
    timestamp: float
    watts: float
