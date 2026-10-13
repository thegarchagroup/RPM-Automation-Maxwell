from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel


class InspectionItemResult(BaseModel):
    id: Optional[int] = None
    checklist_item_id: int
    result: str  # pass, fail, na
    remark: Optional[str] = None  # RPM remark
    inspector_remark: Optional[str] = None  # Inspector remark
    photo_url: Optional[str] = None
    is_fixed: Optional[bool] = False
    fixed_at: Optional[datetime] = None
    fixed_by: Optional[str] = None
    fixed_remark: Optional[str] = None


class DefectItemFixRequest(BaseModel):
    is_fixed: bool = True
    fixed_remark: Optional[str] = None
    fixed_by: Optional[str] = "Admin"


class DefectBulkFixRequest(BaseModel):
    fixed_remark: Optional[str] = None
    fixed_by: Optional[str] = "Admin"
    item_ids: Optional[List[int]] = None


class InspectionCreate(BaseModel):
    room_number: str
    room_type: str
    inspection_date: str
    property_name: Optional[str] = "Maxwell"
    quarter: Optional[str] = None
    status: str = "in_progress"
    defects_status: Optional[str] = "open"
    maintenance_carried_by: Optional[str] = None
    inspected_by: Optional[str] = None
    signature_url: Optional[str] = None
    inspected_by_signature_url: Optional[str] = None
    overall_remark: Optional[str] = None
    inspector_remark: Optional[str] = None
    items: List[InspectionItemResult] = []


class InspectionUpdate(BaseModel):
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    inspection_date: Optional[str] = None
    property_name: Optional[str] = None
    quarter: Optional[str] = None
    status: Optional[str] = None
    defects_status: Optional[str] = None
    maintenance_carried_by: Optional[str] = None
    inspected_by: Optional[str] = None
    signature_url: Optional[str] = None
    inspected_by_signature_url: Optional[str] = None
    overall_remark: Optional[str] = None
    inspector_remark: Optional[str] = None
    items: Optional[List[InspectionItemResult]] = None


class InspectionResponse(BaseModel):
    id: int
    room_number: str
    room_type: str
    inspection_date: str
    property_name: Optional[str] = "Maxwell"
    quarter: Optional[str] = None
    status: str
    defects_status: Optional[str] = "open"
    defects_completed_at: Optional[datetime] = None
    maintenance_carried_by: Optional[str] = None
    inspected_by: Optional[str] = None
    signature_url: Optional[str] = None
    inspected_by_signature_url: Optional[str] = None
    overall_remark: Optional[str] = None
    inspector_remark: Optional[str] = None
    started_at: datetime
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[InspectionItemResult] = []

    class Config:
        from_attributes = True
