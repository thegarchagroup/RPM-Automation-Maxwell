from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel


class InspectionItemResult(BaseModel):
    checklist_item_id: int
    result: str  # pass, fail, na
    remark: Optional[str] = None
    photo_url: Optional[str] = None


class InspectionCreate(BaseModel):
    room_number: str
    room_type: str
    inspection_date: str
    status: str = "in_progress"
    maintenance_carried_by: Optional[str] = None
    inspected_by: Optional[str] = None
    signature_url: Optional[str] = None
    overall_remark: Optional[str] = None
    items: List[InspectionItemResult] = []


class InspectionUpdate(BaseModel):
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    inspection_date: Optional[str] = None
    status: Optional[str] = None
    maintenance_carried_by: Optional[str] = None
    inspected_by: Optional[str] = None
    signature_url: Optional[str] = None
    overall_remark: Optional[str] = None
    items: Optional[List[InspectionItemResult]] = None


class InspectionResponse(BaseModel):
    id: int
    room_number: str
    room_type: str
    inspection_date: str
    status: str
    maintenance_carried_by: Optional[str] = None
    inspected_by: Optional[str] = None
    signature_url: Optional[str] = None
    overall_remark: Optional[str] = None
    started_at: datetime
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[InspectionItemResult] = []

    class Config:
        from_attributes = True
