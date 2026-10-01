from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RpmRecordBase(BaseModel):
    property_name: str = "MAXWELL RESERVE"
    year: int = 2026
    quarter: str = "2nd Quarter May-August 2026"
    floor: str
    category: str = "guest_room"
    room_or_area: str
    eng_date: Optional[str] = None
    ac_servicing: Optional[str] = None
    housekeeping: Optional[str] = None
    inspection_status: str = "Pending"
    inspection_date: Optional[str] = None
    remarks: Optional[str] = None
    sort_order: int = 0


class RpmRecordCreate(RpmRecordBase):
    pass


class RpmRecordUpdate(BaseModel):
    floor: Optional[str] = None
    category: Optional[str] = None
    room_or_area: Optional[str] = None
    eng_date: Optional[str] = None
    ac_servicing: Optional[str] = None
    housekeeping: Optional[str] = None
    inspection_status: Optional[str] = None
    inspection_date: Optional[str] = None
    remarks: Optional[str] = None
    sort_order: Optional[int] = None


class RpmRecordResponse(RpmRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FloorStats(BaseModel):
    floor: str
    total: int
    completed: int
    pending: int
    completion_rate: float  # e.g., 85.5%


class DashboardStats(BaseModel):
    property_name: str
    quarter: str
    year: int
    total_units: int
    total_rooms: int
    total_public_areas: int
    completed_count: int
    pending_count: int
    overall_completion_rate: float
    floor_stats: List[FloorStats]
    recent_completed: List[RpmRecordResponse] = []


class FloorMatrixResponse(BaseModel):
    property_name: str
    quarter: str
    year: int
    floors: Dict[str, List[RpmRecordResponse]]
